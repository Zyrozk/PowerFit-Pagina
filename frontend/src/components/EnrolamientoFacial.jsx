import { useEffect, useState } from "react";
import API_URL from "../services/api";
import RegistroFacial from "./RegistroFacial";

function EnrolamientoFacial({ accessToken, volver }) {
  const [socios, setSocios] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const [busquedaAplicada, setBusquedaAplicada] = useState("");
  const [socioSeleccionado, setSocioSeleccionado] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controlador = new AbortController();

    const obtenerSocios = async () => {
      setCargando(true);
      setError("");

      try {
        const parametros = new URLSearchParams();

        if (busquedaAplicada.trim()) {
          parametros.set("buscar", busquedaAplicada.trim());
        }

        const consulta = parametros.toString();

        const url = `${API_URL}/usuarios/socios/${
          consulta ? `?${consulta}` : ""
        }`;

        const respuesta = await fetch(url, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          signal: controlador.signal,
        });

        if (!respuesta.ok) {
          throw new Error(
            "No se pudo obtener el listado de socios."
          );
        }

        const datos = await respuesta.json();
        setSocios(datos);
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        if (!controlador.signal.aborted) {
          setCargando(false);
        }
      }
    };

    obtenerSocios();

    return () => controlador.abort();
  }, [accessToken, busquedaAplicada]);

  const buscarSocios = (e) => {
    e.preventDefault();
    setBusquedaAplicada(busqueda);
  };

  const limpiarBusqueda = () => {
    setBusqueda("");
    setBusquedaAplicada("");
  };

  const seleccionarSocio = (socio) => {
    setSocioSeleccionado(socio);
  };

  const volverASocios = () => {
    setSocioSeleccionado(null);
  };

  if (socioSeleccionado) {
    return (
      <RegistroFacial
        socio={socioSeleccionado}
        accessToken={accessToken}
        volver={() => setSocioSeleccionado(null)}
        />
    );
  }

  return (
    <div className="panel-contenedor">
      <main className="panel-contenido">
        <button
          className="panel-salir"
          onClick={volver}
        >
          Volver al panel
        </button>

        <div className="panel-bienvenida">
          <h2>Enrolamiento facial</h2>
          <p>
            Busca a un socio para consultar el estado de su
            reconocimiento facial.
          </p>
        </div>

        <form
          className="busqueda-socios"
          onSubmit={buscarSocios}
        >
          <div className="campo">
            <label htmlFor="buscarSocio">
              Buscar socio
            </label>

            <input
              id="buscarSocio"
              type="text"
              placeholder="Nombre, apellido o usuario"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="opcion-boton"
          >
            Buscar
          </button>

          <button
            type="button"
            className="panel-salir"
            onClick={limpiarBusqueda}
          >
            Limpiar
          </button>
        </form>

        {cargando && <p>Cargando socios...</p>}

        {error && (
          <p style={{ color: "#dc3545" }}>
            {error}
          </p>
        )}

        {!cargando && !error && (
          <div className="lista-socios">
            {socios.length === 0 ? (
              <p>No se encontraron socios.</p>
            ) : (
              socios.map((socio) => (
                <div
                  className="socio-tarjeta"
                  key={socio.id}
                >
                  <div>
                    <h3>
                      {socio.first_name} {socio.last_name}
                    </h3>

                    <p>
                      Usuario: {socio.username}
                    </p>

                    <span
                      className={
                        socio.reconocimiento_facial_habilitado
                          ? "estado-facial activo"
                          : "estado-facial inactivo"
                      }
                    >
                      {socio.reconocimiento_facial_habilitado
                        ? "Reconocimiento facial activo"
                        : "Sin reconocimiento facial"}
                    </span>
                  </div>

                  <button
                    type="button"
                    className="opcion-boton"
                    onClick={() => seleccionarSocio(socio)}
                  >
                    {socio.reconocimiento_facial_habilitado
                      ? "Actualizar rostro"
                      : "Registrar rostro"}
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default EnrolamientoFacial;