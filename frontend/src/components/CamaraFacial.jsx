
import { useEffect, useRef, useState } from "react";
import API_URL, { apiFetch } from "../services/api";

function CamaraFacial({
  socio,
  accessToken,
  volver,
  alGuardar,
}) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const montadoRef = useRef(false);

  const [camaraActiva, setCamaraActiva] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [fotografia, setFotografia] = useState(null);
  const [archivoFotografia, setArchivoFotografia] = useState(null);
  const [guardado, setGuardado] = useState(false);

  const detenerCamara = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        track.stop();
      });

      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCamaraActiva(false);
  };

  const iniciarCamara = async () => {
    setError("");
    setCargando(true);
    setFotografia(null);
    setArchivoFotografia(null);

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(
          "Este navegador no permite acceder a la cámara."
        );
      }

      const stream =
        await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "user",
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });

      if (!montadoRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }

      streamRef.current = stream;
      setCamaraActiva(true);
    } catch (err) {
      detenerCamara();

      if (err.name === "NotAllowedError") {
        setError(
          "No se otorgó permiso para utilizar la cámara."
        );
      } else if (err.name === "NotFoundError") {
        setError(
          "No se encontró una cámara conectada al computador."
        );
      } else {
        setError(
          err.message || "No se pudo iniciar la cámara."
        );
      }
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    if (
      camaraActiva &&
      videoRef.current &&
      streamRef.current
    ) {
      const video = videoRef.current;

      video.srcObject = streamRef.current;

      video.play().catch(() => {
        setError("No se pudo reproducir la cámara.");
      });
    }
  }, [camaraActiva]);

  const capturarRostro = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (
      !video ||
      !canvas ||
      video.readyState < 2 ||
      !video.videoWidth ||
      !video.videoHeight
    ) {
      setError("La cámara todavía no está lista.");
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const contexto = canvas.getContext("2d");

    if (!contexto) {
      setError("No se pudo capturar la fotografía.");
      return;
    }

    contexto.drawImage(
      video,
      0,
      0,
      canvas.width,
      canvas.height
    );

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setError("No se pudo generar la fotografía.");
          return;
        }

        if (blob.size > 5 * 1024 * 1024) {
          setError("La fotografía supera el máximo de 5 MB.");
          return;
        }

        const archivo = new File(
          [blob],
          "rostro.jpeg",
          { type: "image/jpeg" }
        );

        setArchivoFotografia(archivo);
        setFotografia(
          canvas.toDataURL("image/jpeg", 0.9)
        );

        detenerCamara();
        setError("");
      },
      "image/jpeg",
      0.9
    );
  };

  const repetirFotografia = () => {
    setFotografia(null);
    setArchivoFotografia(null);
    setError("");
    iniciarCamara();
  };

  const confirmarFotografia = async () => {
    if (guardando || guardado) {
      return;
    }

    if (!archivoFotografia) {
      setError("Primero debes capturar una fotografía.");
      return;
    }

    setGuardando(true);
    setError("");

    try {
      const formulario = new FormData();

      formulario.append("socio_id", String(socio.id));
      formulario.append("imagen", archivoFotografia);

      const respuesta = await fetch(
        `${API_URL}/usuarios/enrolamiento-facial/`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          body: formulario,
        }
      );

      const datos = await respuesta.json().catch(() => ({}));

      if (!respuesta.ok) {
        const motivos = Array.isArray(datos.motivos)
          ? datos.motivos.join(" ")
          : "";

        throw new Error(
          [
            datos.error ||
              datos.detail ||
              "No se pudo guardar el registro facial.",
            motivos,
          ].filter(Boolean).join(" ")
        );
      }

      if (
        respuesta.status !== 201 ||
        datos.activo !== true ||
        datos.reconocimiento_facial_habilitado !== true
      ) {
        throw new Error(
          "No se pudo confirmar la activación del registro facial."
        );
      }

      setGuardado(true);
      setFotografia(null);
      setArchivoFotografia(null);

      if (canvasRef.current) {
        canvasRef.current.width = 0;
        canvasRef.current.height = 0;
      }

      detenerCamara();
    } catch (err) {
      setError(
        err.message || "Ocurrió un error durante el enrolamiento."
      );
    } finally {
      setGuardando(false);
    }
  };

  useEffect(() => {
    montadoRef.current = true;

    return () => {
      montadoRef.current = false;

      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => {
          track.stop();
        });

        streamRef.current = null;
      }
    };
  }, []);

  const nombreCompleto =
    `${socio.first_name} ${socio.last_name}`.trim() ||
    socio.username;

  if (guardado) {
    return (
      <div className="registro-facial-contenedor">
        <div className="registro-facial-tarjeta">
          <div className="registro-facial-encabezado">
            <div className="registro-facial-icono">
              ✓
            </div>

            <h2>Registro facial exitoso</h2>

            <p>
              Socio: <strong>{nombreCompleto}</strong>
            </p>
          </div>

          <div className="camara-instrucciones">
            <h3>Reconocimiento facial activo</h3>

            <p>
              El registro facial del socio se ha
              guardado correctamente.
            </p>

            <p>
              Los datos biométricos se encuentran
              almacenados de forma cifrada.
            </p>
          </div>

          <div className="camara-acciones">
            <button
              className="opcion-boton"
              onClick={alGuardar}
            >
              Finalizar enrolamiento
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="registro-facial-contenedor">
      <button
        className="panel-salir"
        disabled={guardando}
        onClick={() => {
          detenerCamara();
          volver();
        }}
      >
        Volver
      </button>

      <div className="registro-facial-tarjeta">
        <div className="registro-facial-encabezado">
          <div className="registro-facial-icono">
            📷
          </div>

          <h2>Cámara de enrolamiento facial</h2>

          <p>
            Socio: <strong>{nombreCompleto}</strong>
          </p>
        </div>

        <div className="camara-contenedor">
          {fotografia ? (
            <img
              src={fotografia}
              alt="Fotografía capturada del socio"
              className="camara-video"
            />
          ) : (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="camara-video"
              />

              {!camaraActiva && (
                <div className="camara-mensaje">
                  <span>📷</span>
                  <p>La cámara está desactivada</p>
                </div>
              )}
            </>
          )}
        </div>

        <canvas
          ref={canvasRef}
          style={{ display: "none" }}
        />

        {error && (
          <p className="camara-error" role="alert">
            {error}
          </p>
        )}

        <div className="camara-instrucciones">
          <h3>
            {fotografia
              ? "Confirmar fotografía"
              : "Indicaciones para el socio"}
          </h3>

          {fotografia ? (
            <p>
              Comprueba que el rostro sea visible antes
              de confirmar y guardar el registro facial.
            </p>
          ) : (
            <>
              <p>
                Colócate frente a la cámara, mantén el
                rostro visible y procura tener buena
                iluminación.
              </p>

              <p>
                Evita cubrir tu rostro con objetos que
                puedan dificultar su identificación.
              </p>
            </>
          )}
        </div>

        <div className="camara-acciones">
          {!camaraActiva && !fotografia && (
            <button
              className="opcion-boton"
              onClick={iniciarCamara}
              disabled={cargando}
            >
              {cargando
                ? "Iniciando cámara..."
                : "Activar cámara"}
            </button>
          )}

          {camaraActiva && (
            <>
              <button
                className="opcion-boton"
                onClick={capturarRostro}
              >
                📸 Capturar rostro
              </button>

              <button
                className="panel-salir"
                onClick={detenerCamara}
              >
                Desactivar cámara
              </button>
            </>
          )}

          {fotografia && (
            <>
              <button
                className="panel-salir"
                onClick={repetirFotografia}
                disabled={guardando}
              >
                Repetir fotografía
              </button>

              <button
                className="opcion-boton"
                onClick={confirmarFotografia}
                disabled={guardando || !archivoFotografia}
              >
                {guardando
                  ? "Guardando registro facial..."
                  : "Confirmar y guardar"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default CamaraFacial;
