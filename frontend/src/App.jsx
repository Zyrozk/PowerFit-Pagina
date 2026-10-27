import { useState } from "react";
import API_URL from "./services/api";
import PanelDuena from "./components/PanelDuena";
import HistorialPagos from "./components/HistorialPagos";
import EnrolamientoFacial from "./components/EnrolamientoFacial";
import "./App.css";

function App() {
  const [usuario, setUsuario] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [sesion, setSesion] = useState(null);
  const [pantalla, setPantalla] = useState("panel");

  const iniciarSesion = async (e) => {
    e.preventDefault();
    setError("");
    setCargando(true);

    try {
      const respuesta = await fetch(`${API_URL}/token/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: usuario,
          password: contrasena,
        }),
      });

      if (!respuesta.ok) {
        throw new Error("Usuario o contraseña incorrectos.");
      }

      const tokens = await respuesta.json();

      const respuestaPerfil = await fetch(
        `${API_URL}/usuarios/mi-perfil/`,
        {
          headers: {
            Authorization: `Bearer ${tokens.access}`,
          },
        }
      );

      if (!respuestaPerfil.ok) {
        throw new Error("No se pudo verificar la cuenta.");
      }

      const perfil = await respuestaPerfil.json();

      if (perfil.rol !== "DUENA") {
        throw new Error(
          "No tienes permisos para acceder al panel de administración."
        );
      }

      setSesion({
        usuario: perfil,
        accessToken: tokens.access,
      });

      setPantalla("panel");
      setContrasena("");
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  const cerrarSesion = () => {
    setSesion(null);
    setUsuario("");
    setContrasena("");
    setError("");
    setPantalla("panel");
  };

  if (sesion) {
    if (pantalla === "historial") {
      return (
        <HistorialPagos
          accessToken={sesion.accessToken}
          volver={() => setPantalla("panel")}
        />
      );
    }

    if (pantalla === "enrolamiento") {
      return (
        <EnrolamientoFacial
          accessToken={sesion.accessToken}
          volver={() => setPantalla("panel")}
        />
      );
    }

    return (
      <PanelDuena
        usuario={sesion.usuario}
        cerrarSesion={cerrarSesion}
        verHistorial={() => setPantalla("historial")}
        verEnrolamiento={() => setPantalla("enrolamiento")}
      />
    );
  }

  return (
    <div className="contenedor">
      <div className="login-tarjeta">
        <div className="login-encabezado">
          <div className="login-icono">P</div>
          <h1>PowerFit Copiapó</h1>
          <p>Panel de Administración</p>
        </div>

        <form
          onSubmit={iniciarSesion}
          className="login-formulario"
        >
          <div className="campo">
            <label htmlFor="usuario">Usuario</label>

            <input
              id="usuario"
              type="text"
              placeholder="Ingresa tu usuario"
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <div className="campo">
            <label htmlFor="contrasena">Contraseña</label>

            <input
              id="contrasena"
              type="password"
              placeholder="Ingresa tu contraseña"
              value={contrasena}
              onChange={(e) => setContrasena(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <p style={{ color: "#dc3545", fontSize: "14px" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            className="boton-ingresar"
            disabled={cargando}
          >
            {cargando ? "Ingresando..." : "Iniciar sesión"}
          </button>
        </form>

        <p className="login-pie">
          Acceso exclusivo para la administración
        </p>
      </div>
    </div>
  );
}

export default App;