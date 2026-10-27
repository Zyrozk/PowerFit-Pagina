import { useEffect, useState } from "react";
import { API_URL } from "../services/api";
import CamaraFacial from "./CamaraFacial";

function RegistroFacial({ socio, accessToken, volver }) {
  const [consentimiento, setConsentimiento] = useState(false);
  const [mostrarCamara, setMostrarCamara] = useState(false);
  const [estadoFacial, setEstadoFacial] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controlador = new AbortController();

    const consultarEstado = async () => {
      setCargando(true);
      setError("");
      setEstadoFacial(null);

      try {
        const respuesta = await fetch(
          `${API_URL}/usuarios/socios/${socio.id}/registro-facial/`,
          {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
            signal: controlador.signal,
          }
        );

        if (!respuesta.ok) {
          throw new Error(
            "No se pudo consultar el estado del registro facial."
          );
        }

        const datos = await respuesta.json();
        setEstadoFacial(datos);
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

    consultarEstado();

    return () => controlador.abort();
  }, [socio.id, accessToken]);

  const nombreCompleto =
    `${socio.first_name} ${socio.last_name}`.trim() ||
    socio.username;

  if (mostrarCamara) {
    return (
      <CamaraFacial
        socio={socio}
        volver={() => setMostrarCamara(false)}
      />
    );
  }

  return (
    <div className="registro-facial-contenedor">
      <button className="panel-salir" onClick={volver}>
        Volver
      </button>

      <div className="registro-facial-tarjeta">
        <div className="registro-facial-encabezado">
          <div className="registro-facial-icono">👤</div>

          <h2>Registro facial del socio</h2>

          <p>
            Socio: <strong>{nombreCompleto}</strong>
          </p>
        </div>

        {cargando && (
          <p>Consultando el estado del registro facial...</p>
        )}

        {error && <p className="camara-error">{error}</p>}

        {!cargando && !error && estadoFacial && (
          <>
            <div className="camara-instrucciones">
              <h3>Estado del enrolamiento</h3>

              {estadoFacial.activo ? (
                <p>
                  🟢 El socio tiene un registro facial activo.
                </p>
              ) : estadoFacial.tiene_registro ? (
                <p>
                  🟡 El socio tiene un registro facial creado,
                  pero todavía no está activo.
                </p>
              ) : (
                <p>
                  ⚪ El socio todavía no tiene un registro
                  facial.
                </p>
              )}

              <p>
                Consentimiento registrado:{" "}
                <strong>
                  {estadoFacial.consentimiento_otorgado
                    ? "Sí"
                    : "No"}
                </strong>
              </p>
            </div>

            <div className="camara-instrucciones">
              <h3>Autorización del socio</h3>

              <p>
                El reconocimiento facial es opcional y se
                utilizará para verificar la identidad del
                socio durante el control de asistencia.
              </p>

              <p>
                Antes de continuar, informa al socio sobre
                el uso de sus datos y confirma que desea
                participar voluntariamente.
              </p>

              <label>
                <input
                  type="checkbox"
                  checked={consentimiento}
                  onChange={(e) =>
                    setConsentimiento(e.target.checked)
                  }
                />{" "}
                Confirmo que se informó al socio y que
                manifestó su autorización para continuar
                con la captura.
              </label>

              <p>
                Esta confirmación es preliminar y no
                constituye todavía un registro verificable
                del consentimiento del socio.
              </p>
            </div>

            <div className="camara-acciones">
              <button
                className="opcion-boton"
                disabled={
                  !consentimiento ||
                  estadoFacial.activo
                }
                onClick={() => setMostrarCamara(true)}
              >
                Continuar a la cámara
              </button>
            </div>

            {estadoFacial.activo && (
              <p>
                Para actualizar un registro facial activo
                utilizaremos posteriormente un procedimiento
                especial autorizado por la DUEÑA.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default RegistroFacial;