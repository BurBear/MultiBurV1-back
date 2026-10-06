# Tiempo efectivo de produccion

Las predicciones nuevas, las tendencias y la comparacion de duracion real usan
solo los intervalos trabajados. `PAUSAR` detiene la suma y `REANUDAR` la continua.
Las incidencias del operador se reportan desde un proceso pausado: todo el
intervalo hasta reanudar queda excluido, incluso despues de cerrar la incidencia.

Ejemplo: 30 minutos trabajando + 20 en pausa + 10 trabajando = 40 minutos reales.
La precision sigue siendo minutos enteros; se redondea al terminar el calculo.

En T+R se usa el historial de cada lado (TIRA/RETIRA). Se excluyen sus pausas y
las esperas entre lados. Si hay lados simultaneos, cada segundo con algun lado
trabajando se cuenta una sola vez en la duracion del proceso de impresion.

Las reaperturas tampoco suman la espera entre finalizar y volver a reanudar.

## Despliegue e historicos

- Desplegar el backend de `RamaDeploy`. No se requiere migracion ni cambiar el frontend.
- Se reutilizan `ordenes_procesos`, `orden_proceso_historial` y `orden_impresion_juegos`.
- Las ordenes anteriores con historial de pausas se recalculan al consultar
  tendencias o generar una nueva prediccion. No se modifican sus fechas.
- Las predicciones ya guardadas son registros historicos: generar otra prediccion
  para obtener la nueva estimacion; usar la comparacion con duracion real para
  actualizar una comparacion anterior.
- Sin historial de pausas no se puede reconstruir una espera desconocida. Para
  esos registros se conservan las fechas disponibles como referencia.
- Las estimaciones base sin muestras historicas suficientes no cambian.

## Verificacion local

Con las dependencias de `requirements.txt` y `pytest` instaladas:

```powershell
python -m pytest tests -q
```

Las pruebas de integracion usan SQLite en memoria, sin acceder a la base del sistema.
