
import { useEffect, useState } from "react";
import API_URL, { apiFetch } from "../services/api";
import CamaraFacial from "./CamaraFacial";

function RegistroFacial({ socio, accessToken, volver }) {
  const [consentimiento, setConsentimiento] = useState(false);
  const [mostrarCamara, setMostrarCamara] = useState(false);
  const [estadoFacial, setEstadoFacial] = useState(null);
  const [condiciones, setCondiciones] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [actualizacion, setActualizacion] = useState(0);

  useEffect(() => {
    const controlador = new AbortController();

    const consultarEstado = async () => {
      setCargando(true);
      setError("");
      setEstadoFacial(null);
      setCondiciones(null);

      try {
        const opciones = {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          signal: controlador.signal,
        };

        const [respuestaEstado, respuestaCondiciones] =
          await Promise.all([
            fetch(
              `${API_URL}/usuarios/socios/${socio.id}/registro-facial/`,
              opciones
            ),
            fetch(
              `${API_URL}/usuarios/enrolamiento-facial/?socio_id=${socio.id}`,
              opciones
            ),
          ]);

        if (!respuestaEstado.ok) {
          throw new Error(
            "No se pudo consultar el estado del registro facial."
          );
        }

        if (!respuestaCondiciones.ok) {
          throw new Error(
            "No se pudieron comprobar las condiciones del enrolamiento."
          );
        }

        const datosEstado = await respuestaEstado.json();
        const datosCondiciones =
          await respuestaCondiciones.json();

        setEstadoFacial(datosEstado);
        setCondiciones(datosCondiciones);
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
  }, [socio.id, accessToken, actualizacion]);

  const nombreCompleto =
    `${socio.first_name} ${socio.last_name}`.trim() ||
    socio.username;

  const enrolamientoDisponible =
    condiciones?.enrolamiento_disponible === true &&
    estadoFacial?.activo === false;

  const actualizarEstado = () => {
    setConsentimiento(false);
    setActualizacion((anterior) => anterior + 1);
  };

  const finalizarEnrolamiento = () => {
    setMostrarCamara(false);
    actualizarEstado();
  };

  if (mostrarCamara) {
    return (
      <CamaraFacial
        socio={socio}
        accessToken={accessToken}
        volver={() => {
          setMostrarCamara(false);
          actualizarEstado();
        }}
        alGuardar={finalizarEnrolamiento}
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
          <div className="registro-facial-icono">
            👤
          </div>

          <h2>Registro facial del socio</h2>

          <p>
            Socio: <strong>{nombreCompleto}</strong>
          </p>
        </div>

        {cargando && (
          <p>Consultando el estado del registro facial...</p>
        )}

        {error && (
          <p className="camara-error">{error}</p>
        )}

        {!cargando &&
          !error &&
          estadoFacial &&
          condiciones && (
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
                    ⚪ El socio todavía no tiene un registro facial.
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

                <p>
                  Consentimiento confirmado por el socio:{" "}
                  <strong>
                    {estadoFacial.consentimiento_confirmado_por_socio
                      ? "Sí"
                      : "No"}
                  </strong>
                </p>
              </div>

              {!estadoFacial.activo &&
                !enrolamientoDisponible && (
                  <div className="camara-instrucciones">
                    <h3>Enrolamiento no disponible</h3>

                    {condiciones.motivos?.map(
                      (motivo, indice) => (
                        <p key={indice}>{motivo}</p>
                      )
                    )}

                    <p>
                      El socio debe cumplir las condiciones
                      requeridas antes de registrar su rostro.
                    </p>
                  </div>
                )}

              {enrolamientoDisponible && (
                <>
                  <div className="camara-instrucciones">
                    <h3>Autorización del socio</h3>

                    <p>
                      El reconocimiento facial es opcional y
                      se utilizará para verificar la identidad
                      del socio durante el control de asistencia.
                    </p>

                    <p>
                      El consentimiento biométrico del socio
                      fue validado por el sistema.
                    </p>

                    <label>
                      <input
                        type="checkbox"
                        checked={consentimiento}
                        onChange={(e) =>
                          setConsentimiento(e.target.checked)
                        }
                      />{" "}
                      Confirmo que el socio está presente
                      y acepta continuar con la captura.
                    </label>
                  </div>

                  <div className="camara-acciones">
                    <button
                      className="opcion-boton"
                      disabled={!consentimiento}
                      onClick={() => setMostrarCamara(true)}
                    >
                      Continuar a la cámara
                    </button>
                  </div>
                </>
              )}

              {estadoFacial.activo && (
                <div className="camara-instrucciones">
                  <h3>Registro facial completado</h3>

                  <p>
                    El reconocimiento facial se encuentra
                    activo para este socio.
                  </p>

                  <p>
                    No es necesario realizar un nuevo
                    enrolamiento.
                  </p>
                </div>
              )}
            </>
          )}

        {!cargando && (
          <div className="camara-acciones">
            <button
              className="panel-salir"
              onClick={actualizarEstado}
            >
              Actualizar estado
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default RegistroFacial;
