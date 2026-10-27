function PanelDuena({
  usuario,
  cerrarSesion,
  verHistorial,
  verEnrolamiento,
}) {
  return (
    <div className="panel-contenedor">
      <header className="panel-header">
        <div className="panel-marca">
          <div className="panel-logo">P</div>

          <div>
            <h1>PowerFit Copiapó</h1>
            <p>Panel de Administración</p>
          </div>
        </div>

        <button className="panel-salir" onClick={cerrarSesion}>
          Cerrar sesión
        </button>
      </header>

      <main className="panel-contenido">
        <div className="panel-bienvenida">
          <h2>
            ¡Bienvenida, {usuario.first_name || usuario.username}!
          </h2>

          <p>
            Selecciona una de las opciones para administrar
            PowerFit Copiapó.
          </p>
        </div>

        <div className="panel-opciones">
          <div className="panel-opcion">
            <div className="opcion-icono">📊</div>

            <h3>Historial de pagos</h3>

            <p>
              Consulta los pagos de los socios, filtra por fechas
              y exporta los registros a Excel.
            </p>

            <button
              className="opcion-boton"
              onClick={verHistorial}
            >
              Ver historial
            </button>
          </div>

          <div className="panel-opcion">
            <div className="opcion-icono">📷</div>

            <h3>Enrolamiento facial</h3>

            <p>
              Registra el rostro de los socios para habilitar
              el reconocimiento facial en el control de asistencia.
            </p>

            <button
              className="opcion-boton"
              onClick={verEnrolamiento}
            >
              Registrar rostro
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

export default PanelDuena;