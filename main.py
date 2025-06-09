from datetime import datetime, timedelta
import pandas as pd
from domain.dataset_api import DatasetAPIi # Asegúrate de que INDECAPI esté en tu PYTHONPATH o en el mismo archivo/directorio
# from data.data_saver import DataSaver # Descomenta si ya tienes tu clase DataSaver implementada

# --- Configuración y Obtención de Datos ---

def main():
    """
    Función principal de la aplicación para cargar datos del INDEC
    y realizar la lógica de comparación de sueldos con inflación.
    """
    print("Iniciando la aplicación de análisis de sueldo vs. inflación...")

    # 1. Definir el período de tiempo para la consulta de inflación
    # La API del INDEC publica datos con un rezago. Para asegurar la disponibilidad,
    # buscaremos datos hasta dos meses antes del mes actual.
    current_date = datetime.now()
    
    # Calcular la fecha de fin para la API: dos meses antes del mes actual
    # Esto asegura que los datos del IPC estén publicados.
    # Por ejemplo, si hoy es junio 7, 2025, buscaremos hasta abril 2025.
    if current_date.month <= 2: # Si es enero o febrero, ajustamos el año
        end_date_obj_api = current_date.replace(year=current_date.year - 1, month=current_date.month + 12 - 2, day=1)
    else:
        end_date_obj_api = current_date.replace(month=current_date.month - 2, day=1)
        
    end_date_str_api = end_date_obj_api.strftime('%Y-%m-%d')


    # Fecha de inicio: 14 meses antes de la fecha de fin de la API
    # Esto asegura un rango de 12 meses completos de datos disponibles.
    start_date_obj_api = end_date_obj_api - timedelta(days=30 * 14) # Aprox. 14 meses antes para asegurar 12 completos
    start_date_str_api = start_date_obj_api.strftime('%Y-%m-%d')

    print(f"Período de consulta para el IPC (asegurando disponibilidad): desde {start_date_str_api} hasta {end_date_str_api}")

    # 2. Cargar datos de inflación usando la clase INDECAPI
    indec_api = DatasetAPIi()
    try:
        # Llamamos a cargar_datos con los parámetros esperados por INDECAPI
        indec_api.cargar_datos(series_ids=[indec_api.IPC_NATIONAL_ID],
                               start_date=start_date_str_api,
                               end_date=end_date_str_api)

        if indec_api.datos is not None and not indec_api.datos.empty:
            print("\nDatos de IPC cargados exitosamente.")
            indec_api.mostrar_resumen() # Mostrar un resumen de los datos del IPC
            
            # Asegurarse de que la columna de fecha sea el índice para facilitar la búsqueda
            if 'fecha' in indec_api.datos.columns and not isinstance(indec_api.datos.index, pd.DatetimeIndex):
                indec_api.datos.set_index('fecha', inplace=True)
            elif indec_api.datos.index.name != 'fecha' and isinstance(indec_api.datos.index, pd.DatetimeIndex):
                indec_api.datos.index.name = 'fecha'


            # 3. Simulación de entrada de sueldo del usuario
            # Aquí es donde el usuario ingresaría sus sueldos y fechas.
            # Para el ejemplo, usaremos valores fijos.
            print("\n--- Análisis de Sueldo vs. Inflación ---")

            # Ejemplo: Sueldo de Enero 2024 y Junio 2025 (ajusta las fechas y valores según tu necesidad)
            # Asegúrate de que estas fechas estén dentro del rango de datos del IPC obtenidos.
            # **NOTA**: Las fechas de sueldo deben estar dentro del rango de datos IPC que la API pudo obtener.
            # Ajusta estas fechas según el 'Período de consulta para el IPC' que se imprime.
            sueldo_inicial = 354721.79 # Sueldo neto en la fecha inicial
            fecha_sueldo_inicial_str = '2024-03-01' # Fecha de inicio del sueldo (ajustada para el ejemplo)
            
            sueldo_final = 776493.58 # Sueldo neto en la fecha final
            fecha_sueldo_final_str = '2025-04-01' # Fecha de fin del sueldo (ajustada para el ejemplo)


            print(f"Sueldo inicial: ${sueldo_inicial:.2f} (a partir de {fecha_sueldo_inicial_str})")
            print(f"Sueldo final:   ${sueldo_final:.2f} (a partir de {fecha_sueldo_final_str})")

            # Convertir fechas de sueldo a objetos datetime para comparaciones
            fecha_sueldo_inicial = pd.to_datetime(fecha_sueldo_inicial_str)
            fecha_sueldo_final = pd.to_datetime(fecha_sueldo_final_str)

            # 4. Obtener los índices de IPC para las fechas de sueldo
            try:
                # Buscar el IPC del mes correspondiente a la fecha inicial del sueldo
                # Usamos .to_period('M') para comparar solo el mes y el año
                ipc_inicial_row = indec_api.datos.loc[indec_api.datos.index.to_period('M') == fecha_sueldo_inicial.to_period('M')]
                if ipc_inicial_row.empty:
                    print(f"Error: No se encontró IPC para la fecha inicial del sueldo: {fecha_sueldo_inicial_str}. Asegúrate que la fecha esté dentro del rango de datos obtenidos.")
                    return
                ipc_inicial = ipc_inicial_row.iloc[0][indec_api.IPC_NATIONAL_ID]

                # Obtener el IPC del mes correspondiente a la fecha final del sueldo
                ipc_final_row = indec_api.datos.loc[indec_api.datos.index.to_period('M') == fecha_sueldo_final.to_period('M')]
                if ipc_final_row.empty:
                    print(f"Error: No se encontró IPC para la fecha final del sueldo: {fecha_sueldo_final_str}. Asegúrate que la fecha esté dentro del rango de datos obtenidos.")
                    return
                ipc_final = ipc_final_row.iloc[0][indec_api.IPC_NATIONAL_ID]


                print(f"IPC inicial ({fecha_sueldo_inicial.strftime('%Y-%m')}): {ipc_inicial:.2f}")
                print(f"IPC final   ({fecha_sueldo_final.strftime('%Y-%m')}): {ipc_final:.2f}")

                # 5. Calcular la inflación acumulada
                if ipc_inicial != 0: # Evitar división por cero
                    inflacion_acumulada = ((ipc_final / ipc_inicial) - 1) * 100
                    print(f"Inflación acumulada en el período: {inflacion_acumulada:.2f}%")
                else:
                    print("Advertencia: IPC inicial es cero, no se puede calcular la inflación.")
                    inflacion_acumulada = 0

                # 6. Calcular el incremento salarial
                if sueldo_inicial != 0: # Evitar división por cero
                    incremento_salarial = ((sueldo_final - sueldo_inicial) / sueldo_inicial) * 100
                    print(f"Incremento salarial en el período: {incremento_salarial:.2f}%")
                else:
                    print("Advertencia: Sueldo inicial es cero, no se puede calcular el incremento salarial.")
                    incremento_salarial = 0


                # 7. Comparar y mostrar el resultado
                if incremento_salarial > inflacion_acumulada:
                    print("\n¡Felicitaciones! Tu sueldo le ganó a la inflación en este período. 🎉")
                    diferencia = incremento_salarial - inflacion_acumulada
                    print(f"Le ganó por un {diferencia:.2f} puntos porcentuales.")
                elif incremento_salarial < inflacion_acumulada:
                    print("\nLamentablemente, tu sueldo perdió contra la inflación en este período. 📉")
                    diferencia = inflacion_acumulada - incremento_salarial
                    print(f"Perdió por un {diferencia:.2f} puntos porcentuales.")
                else:
                    print("\nTu sueldo se mantuvo a la par de la inflación en este período. ⚖️")

                # Opcional: Calcular el poder adquisitivo real
                if ipc_inicial != 0:
                    sueldo_real_ajustado = sueldo_final / (ipc_final / ipc_inicial)
                    print(f"El poder adquisitivo de tu sueldo final (${sueldo_final:.2f}) es equivalente a ${sueldo_real_ajustado:.2f} en pesos de la fecha inicial.")

            except KeyError as ke:
                print(f"Error: No se encontró la columna '{indec_api.IPC_NATIONAL_ID}' en los datos cargados o la fecha no tiene datos disponibles. {ke}")
            except Exception as e:
                print(f"Ocurrió un error inesperado durante el cálculo de sueldo vs. inflación: {e}")

        else:
            print("\nNo se pudieron obtener datos del IPC para realizar el análisis.")

    except Exception as e:
        print(f"Error al cargar datos del INDEC: {e}")

    # --- Integración con DataSaver (descomenta si lo necesitas) ---
    # try:
    #     if indec_api.datos is not None and not indec_api.datos.empty:
    #         db = DataSaver()
    #         # Es una buena práctica darle un nombre descriptivo a la tabla
    #         db.guardar_dataframe(indec_api.datos, "ipc_datos_nacionales")
    #         print("\nDatos del IPC guardados en la base de datos.")
    #     else:
    #         print("\nNo hay datos de IPC para guardar.")
    # except NameError:
    #     print("\nAdvertencia: La clase DataSaver no está definida o importada. No se guardarán los datos.")
    # except Exception as e:
    #     print(f"Error al guardar datos con DataSaver: {e}")

if __name__ == "__main__":
    main()

