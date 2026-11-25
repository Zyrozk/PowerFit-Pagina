
export const API_URL = import.meta.env.VITE_API_URL;

let sesionActual = null;

export function configurarSesion(tokens, alExpirar) {
  sesionActual = {
    accessToken: tokens.access,
    refreshToken: tokens.refresh,
    renovacion: null,
    alExpirar,
  };
}

export function limpiarSesion() {
  sesionActual = null;
}

function expirarSesion(sesion) {
  if (sesionActual !== sesion) {
    return;
  }

  sesionActual = null;
  sesion.alExpirar?.();
}

async function renovarToken(sesion) {
  if (sesionActual !== sesion) {
    throw new Error("La sesión ya no está disponible.");
  }

  if (!sesion.refreshToken) {
    expirarSesion(sesion);
    throw new Error("Debes iniciar sesión nuevamente.");
  }

  if (sesion.renovacion) {
    return sesion.renovacion;
  }

  sesion.renovacion = (async () => {
    const respuesta = await fetch(
      `${API_URL}/token/refresh/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          refresh: sesion.refreshToken,
        }),
      }
    );

    if (!respuesta.ok) {
      if ([400, 401, 403].includes(respuesta.status)) {
        expirarSesion(sesion);

        throw new Error(
          "Tu sesión ha expirado. Inicia sesión nuevamente."
        );
      }

      throw new Error(
        "No se pudo renovar la sesión. Inténtalo nuevamente."
      );
    }

    const datos = await respuesta.json();

    if (sesionActual !== sesion) {
      throw new Error("La sesión ya no está disponible.");
    }

    if (!datos.access) {
      expirarSesion(sesion);
      throw new Error("No se recibió un token válido.");
    }

    sesion.accessToken = datos.access;

    if (datos.refresh) {
      sesion.refreshToken = datos.refresh;
    }

    return sesion.accessToken;
  })();

  try {
    return await sesion.renovacion;
  } finally {
    sesion.renovacion = null;
  }
}

export async function apiFetch(url, opciones = {}) {
  const sesion = sesionActual;

  if (!sesion) {
    throw new Error("Debes iniciar sesión nuevamente.");
  }

  const ejecutarSolicitud = (token) => {
    const headers = new Headers(opciones.headers || {});

    headers.set(
      "Authorization",
      `Bearer ${token}`
    );

    return fetch(url, {
      ...opciones,
      headers,
    });
  };

  const tokenUtilizado = sesion.accessToken;

  let respuesta = await ejecutarSolicitud(
    tokenUtilizado
  );

  if (respuesta.status !== 401) {
    return respuesta;
  }

  if (sesionActual !== sesion) {
    throw new Error("La sesión ya no está disponible.");
  }

  const nuevoToken =
    sesion.accessToken !== tokenUtilizado
      ? sesion.accessToken
      : await renovarToken(sesion);

  if (sesionActual !== sesion) {
    throw new Error("La sesión ya no está disponible.");
  }

  respuesta = await ejecutarSolicitud(nuevoToken);

  if (respuesta.status === 401) {
    expirarSesion(sesion);

    throw new Error(
      "Tu sesión ha expirado. Inicia sesión nuevamente."
    );
  }

  return respuesta;
}

export default API_URL;
