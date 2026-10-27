import { useEffect, useState } from "react";
import API_URL from "../services/api";

function HistorialPagos({ accessToken, volver }) {
  const [pagos, setPagos] = useState([]);
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [filtros, setFiltros] = useState({
    inicio: "",
    fin: "",
  });
  const [filtroRapido, setFiltroRapido] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controlador = new AbortController();

    const obtenerPagos = async () => {
      setCargando(true);
      setError("");

      try {
        const parametros = new URLSearchParams();

        if (filtros.inicio) {
          parametros.append("fecha_inicio", filtros.inicio);
        }

        if (filtros.fin) {
          parametros.append("fecha_fin", filtros.fin);
        }

        const consulta = parametros.toString();

        const url = `${API_URL}/pagos/historial/${
          consulta ? `?${consulta}` : ""
        }`;

        const respuesta = await fetch(url, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          signal: controlador.signal,
        });

        if (!respuesta.ok) {
          throw new Error("No se pudo obtener el historial de pagos.");
        }

        const datos = await respuesta.json();
        setPagos(datos);
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

    obtenerPagos();

    return () => controlador.abort();
  }, [accessToken, filtros]);

  const convertirFecha = (fecha) => {
    const anio = fecha.getFullYear();
    const mes = String(fecha.getMonth() + 1).padStart(2, "0");
    const dia = String(fecha.getDate()).padStart(2, "0");

    return `${anio}-${mes}-${dia}`;
  };

  const aplicarFiltroRapido = (tipo) => {
    const hoy = new Date();
    const inicio = new Date(
      hoy.getFullYear(),
      hoy.getMonth(),
      hoy.getDate()
    );

    if (tipo === "semana") {
      inicio.setDate(inicio.getDate() - 7);
    }

    if (tipo === "mes") {
      inicio.setMonth(inicio.getMonth() - 1);
    }

    if (tipo === "seis_meses") {
      inicio.setMonth(inicio.getMonth() - 6);
    }

    const fechaDesde = convertirFecha(inicio);
    const fechaHasta = convertirFecha(hoy);

    setFechaInicio(fechaDesde);
    setFechaFin(fechaHasta);

    setFiltroRapido(tipo);
    setError("");

    setFiltros({
      inicio: fechaDesde,
      fin: fechaHasta,
    });
  };

  const aplicarFiltros = (e) => {
    e.preventDefault();

    if (fechaInicio && fechaFin && fechaInicio > fechaFin) {
      setError(
        "La fecha de inicio no puede ser posterior a la fecha de término."
      );
      return;
    }

    setError("");
    setFiltroRapido("");

    setFiltros({
      inicio: fechaInicio,
      fin: fechaFin,
    });
  };

  const limpiarFiltros = () => {
    setFechaInicio("");
    setFechaFin("");
    setFiltroRapido("");
    setError("");

    setFiltros({
      inicio: "",
      fin: "",
    });
  };

  const [exportando, setExportando] = useState(false);
const [errorExportacion, setErrorExportacion] = useState("");

const exportarExcel = async () => {
  setErrorExportacion("");
  setExportando(true);

  try {
    const parametros = new URLSearchParams();

    if (filtros.inicio) {
      parametros.append("fecha_inicio", filtros.inicio);
    }

    if (filtros.fin) {
      parametros.append("fecha_fin", filtros.fin);
    }

    const consulta = parametros.toString();

    const url = `${API_URL}/pagos/exportar-excel/${
      consulta ? `?${consulta}` : ""
    }`;

    const respuesta = await fetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!respuesta.ok) {
      throw new Error("No se pudo exportar el historial de pagos.");
    }

    const archivo = await respuesta.blob();
    const enlaceTemporal = URL.createObjectURL(archivo);

    const formatearFechaArchivo = (fecha) => {
  if (!fecha) return "";

  const [anio, mes, dia] = fecha.split("-");
  return `${dia}-${mes}-${anio}`;
};

    let nombreArchivo = "historial_pagos_completo.xlsx";

    if (filtros.inicio && filtros.fin) {
    const inicio = formatearFechaArchivo(filtros.inicio);
    const fin = formatearFechaArchivo(filtros.fin);

    nombreArchivo = `historial_pagos_${inicio}_al_${fin}.xlsx`;
    } else if (filtros.inicio) {
    const inicio = formatearFechaArchivo(filtros.inicio);

    nombreArchivo = `historial_pagos_desde_${inicio}.xlsx`;
    } else if (filtros.fin) {
    const fin = formatearFechaArchivo(filtros.fin);

    nombreArchivo = `historial_pagos_hasta_${fin}.xlsx`;
    }

    const enlace = document.createElement("a");
    enlace.href = enlaceTemporal;
    enlace.download = nombreArchivo;

    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();

    setTimeout(() => URL.revokeObjectURL(enlaceTemporal), 1000);
  } catch (err) {
    setErrorExportacion(err.message);
  } finally {
    setExportando(false);
  }
};

  const formatearMonto = (monto) => {
    return new Intl.NumberFormat("es-CL", {
      style: "currency",
      currency: "CLP",
      maximumFractionDigits: 0,
    }).format(monto);
  };

  const formatearFecha = (fecha) => {
    return new Date(fecha).toLocaleString("es-CL");
  };

  return (
    <div className="panel-contenedor">
      <main className="panel-contenido">
        <button className="panel-salir" onClick={volver}>
          Volver al panel
        </button>

        <div className="panel-bienvenida">
          <h2>Historial de pagos</h2>
          <p>
            Consulta los pagos registrados en PowerFit Copiapó.
          </p>
        </div>

        <div className="filtros-rapidos">
          <h3>Búsqueda rápida</h3>

          <div className="filtros-rapidos-botones">
            <button
              type="button"
              className={`filtro-rapido ${
                filtroRapido === "semana" ? "activo" : ""
              }`}
              onClick={() => aplicarFiltroRapido("semana")}
            >
              Última semana
            </button>

            <button
              type="button"
              className={`filtro-rapido ${
                filtroRapido === "mes" ? "activo" : ""
              }`}
              onClick={() => aplicarFiltroRapido("mes")}
            >
              Último mes
            </button>

            <button
              type="button"
              className={`filtro-rapido ${
                filtroRapido === "seis_meses" ? "activo" : ""
              }`}
              onClick={() => aplicarFiltroRapido("seis_meses")}
            >
              Últimos 6 meses
            </button>
          </div>
        </div>

        <form onSubmit={aplicarFiltros} className="filtros-pagos">
          <div className="campo">
            <label htmlFor="fechaInicio">
              Fecha de inicio
            </label>
            <input
              id="fechaInicio"
              type="date"
              value={fechaInicio}
              onChange={(e) => {
                setFechaInicio(e.target.value);
                setFiltroRapido("");
              }}
            />
          </div>

          <div className="campo">
            <label htmlFor="fechaFin">
              Fecha de término
            </label>
            <input
              id="fechaFin"
              type="date"
              value={fechaFin}
              onChange={(e) => {
                setFechaFin(e.target.value);
                setFiltroRapido("");
              }}
            />
          </div>

          <button type="submit" className="opcion-boton">
            Filtrar
          </button>

          <button
            type="button"
            className="panel-salir"
            onClick={limpiarFiltros}
          >
            Limpiar
          </button>
        </form>


        <div className="exportar-contenedor">
        <button
            type="button"
            className="opcion-boton"
            onClick={exportarExcel}
            disabled={exportando || cargando || Boolean(error)}
        >
            {exportando ? "Exportando..." : "📥 Exportar a Excel"}
        </button>

        {errorExportacion && (
            <p style={{ color: "#dc3545" }}>
            {errorExportacion}
            </p>
        )}
        </div>

        {cargando && <p>Cargando pagos...</p>}

        {error && (
          <p style={{ color: "#dc3545" }}>{error}</p>
        )}

        {!cargando && !error && (
          <div className="tabla-contenedor">
            <table className="tabla-pagos">
              <thead>
                <tr>
                  <th>Socio</th>
                  <th>Tipo de pago</th>
                  <th>Método</th>
                  <th>Monto</th>
                  <th>Estado</th>
                  <th>Fecha</th>
                </tr>
              </thead>

              <tbody>
                {pagos.map((pago) => (
                  <tr key={pago.id}>
                    <td>{pago.socio_nombre}</td>
                    <td>{pago.tipo_pago_nombre}</td>
                    <td>{pago.metodo_pago_nombre}</td>
                    <td>{formatearMonto(pago.monto)}</td>
                    <td>{pago.estado_nombre}</td>
                    <td>{formatearFecha(pago.fecha_pago)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {pagos.length === 0 && (
              <p>
                No se encontraron pagos para las fechas seleccionadas.
              </p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default HistorialPagos;