import { useEffect, useRef, useState } from "react";

function CamaraFacial({ socio, volver }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const [camaraActiva, setCamaraActiva] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const [fotografia, setFotografia] = useState(null);

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

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(
          "Este navegador no permite acceder a la cámara."
        );
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

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

  const capturarRostro = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas || video.readyState < 2) {
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

    const imagen = canvas.toDataURL("image/jpeg", 0.9);

    setFotografia(imagen);
    detenerCamara();
    setError("");
  };

  const repetirFotografia = () => {
    setFotografia(null);
    iniciarCamara();
  };

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => {
          track.stop();
        });
      }
    };
  }, []);

  const nombreCompleto =
    `${socio.first_name} ${socio.last_name}`.trim() ||
    socio.username;

  return (
    <div className="registro-facial-contenedor">
      <button
        className="panel-salir"
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
          <p className="camara-error">
            {error}
          </p>
        )}

        <div className="camara-instrucciones">
          <h3>Indicaciones para el socio</h3>

          <p>
            Colócate frente a la cámara, mantén el rostro
            visible y procura tener buena iluminación.
          </p>

          <p>
            Evita cubrir tu rostro con objetos que puedan
            dificultar su identificación.
          </p>
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
              >
                Repetir fotografía
              </button>

              <button
                className="opcion-boton"
                disabled
              >
                Confirmar fotografía
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default CamaraFacial;