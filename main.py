import pandas as pd
from datetime import datetime, timedelta

from domain.dataset_api import DatasetAPI
from domain.dataset_csv import DatasetCsv
from domain.dataset_excel import DatasetExcel
from data.data_saver import DataSaver # Asegúrate de tener esta clase implementada y disponible

# La función calcular_inflacion_periodo es genérica y puede quedarse
def calcular_inflacion_periodo(df, fecha_inicio, fecha_fin, valor_columna='ipc_valor'):
    """
    Calcula la inflación acumulada para un período dado.
    Requiere un DataFrame con índice de fechas y una columna de valor (por defecto 'ipc_valor').
    """
    try:
        # Asegurarse de que el índice sea DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha'])
                df = df.set_index('fecha')
            else:
                raise ValueError("El DataFrame no tiene un índice de fecha ni una columna 'fecha'.")
        
        # Asegurarse de que el índice esté ordenado
        df.sort_index(inplace=True)

        # Convertir las fechas de inicio y fin a string 'YYYY-MM' para usar con .loc
        # Esto asume que el índice del DataFrame es el primer día del mes (ej. 2024-01-01)
        fecha_inicio_str_month = fecha_inicio.strftime('%Y-%m-%d')
        fecha_fin_str_month = fecha_fin.strftime('%Y-%m-%d')

        # Buscar el valor de IPC para la fecha de inicio del período
        # Usamos .loc para buscar el índice exacto del mes (primer día).
        # Esto funcionará si tu índice es pd.Timestamp('YYYY-MM-01').
        
        # Primero, intentar un acceso directo. Si falla, buscar la fila que corresponde al mes.
        try:
            ipc_inicio = df.loc[fecha_inicio_str_month, valor_columna]
        except KeyError:
            # Si el día exacto no existe, buscar el mes
            ipc_inicio_series = df.loc[df.index.to_period('M') == fecha_inicio.to_period('M'), valor_columna]
            if ipc_inicio_series.empty:
                print(f"Error: No se encontró IPC para el mes de inicio del período: {fecha_inicio.strftime('%Y-%m')}. Revise el rango de datos.")
                return None
            ipc_inicio = ipc_inicio_series.iloc[0]


        try:
            ipc_fin = df.loc[fecha_fin_str_month, valor_columna]
        except KeyError:
            # Si el día exacto no existe, buscar el mes
            ipc_fin_series = df.loc[df.index.to_period('M') == fecha_fin.to_period('M'), valor_columna]
            if ipc_fin_series.empty:
                print(f"Error: No se encontró IPC para el mes de fin del período: {fecha_fin.strftime('%Y-%m')}. Revise el rango de datos.")
                return None
            ipc_fin = ipc_fin_series.iloc[0]
            
        # Calcular la inflación porcentual
        if ipc_inicio == 0:
            print("Error: IPC inicial es cero. No se puede calcular la inflación.")
            return None
            
        inflacion_porcentual = ((ipc_fin / ipc_inicio) - 1) * 100
        return inflacion_porcentual
    except KeyError:
        print(f"Error: El DataFrame no tiene la columna '{valor_columna}' o el índice no es de tipo fecha.")
        return None
    except Exception as e:
        print(f"Error al calcular la inflación del período: {e}")
        return None

def main():
    print("Bienvenido al Calculador de Inflación.")

    # Rutas de los archivos de datos (ajusta si es necesario)
    csv_file_path = 'file/ipc-chaco-historico.csv'
    excel_file_path = 'file/sh_ipc_05_25.xls'

    # Instanciar los datasets
    dataset_api_indec = DatasetAPI() 
    dataset_csv = DatasetCsv(csv_file_path)
    dataset_excel = DatasetExcel(excel_file_path)

    df_ipc = pd.DataFrame() # Inicializar df_ipc vacío
    source_name = ""
    ipc_value_column_name = 'ipc_valor' # Nombre por defecto para la columna con los valores IPC

    # --- Selección de la fuente de datos ---
    print("\nSeleccione la fuente de datos para el cálculo de inflación:")
    print("1. Datos oficiales del INDEC (API - como en tu main original)")
    print("2. Datos históricos de IPC Chaco (CSV)")
    print("3. Datos de variación mensual (Excel)")

    choice_source = input("Ingrese el número de su elección: ")

    if choice_source == '1':
        print("\nCargando datos del INDEC (API)...")
        current_date = datetime.now()
        
        # Ajuste para obtener datos hasta el mes anterior para la API (más realistas)
        # Si hoy es 11 de junio de 2025, end_date_obj_api será 2025-05-01
        end_date_obj_api = current_date.replace(day=1) - timedelta(days=1) # Retrocede al último día del mes anterior
        end_date_obj_api = end_date_obj_api.replace(day=1) # Luego al primer día de ese mes
        end_date_str_api = end_date_obj_api.strftime('%Y-%m-%d')

        # Fecha de inicio: Un rango adecuado (ej. 5 años para datos de IPC)
        # Esto asegura que tengas suficientes datos para búsquedas de sueldo.
        start_date_obj_api = end_date_obj_api.replace(year=end_date_obj_api.year - 5) 
        start_date_str_api = start_date_obj_api.strftime('%Y-%m-%d')

        print(f"Período de consulta para el IPC (API INDEC): desde {start_date_str_api} hasta {end_date_str_api}")

        try:
            dataset_api_indec.cargar_datos(series_ids=[dataset_api_indec.IPC_NATIONAL_ID],
                                             start_date=start_date_str_api,
                                             end_date=end_date_str_api)

            df_ipc = dataset_api_indec.datos 
            source_name = "INDEC (API)"
            ipc_value_column_name = dataset_api_indec.IPC_NATIONAL_ID 
            
            if df_ipc is not None and not df_ipc.empty:
                # Asegurarse de que el índice sea de fecha para el cálculo posterior
                if 'fecha' in df_ipc.columns:
                    df_ipc.set_index('fecha', inplace=True)
                df_ipc.sort_index(inplace=True) # Muy importante para que .loc funcione correctamente
                print("Datos de IPC INDEC cargados exitosamente.")
            else:
                print("No se pudieron obtener datos del IPC del INDEC.")

        except Exception as e:
            print(f"Error al cargar datos del INDEC: {e}")

    elif choice_source == '2':
        print("\nCargando datos históricos de IPC Chaco (CSV)...")
        dataset_csv.cargar_datos()
        df_ipc = dataset_csv.obtener_datos()
        source_name = "IPC Chaco (CSV)"
        ipc_value_column_name = 'ipc_valor'

    elif choice_source == '3':
        print("\nSeleccione la región para los datos de variación mensual (Excel):")
        print("1. Total Nacional")
        print("2. Región GBA")
        print("3. Región Pampeana")
        print("4. Región Noroeste")
        print("5. Región Noreste")
        print("6. Región Cuyo")
        print("7. Región Patagonia")
        
        region_choice = input("Ingrese el número de su elección de región: ")
        
        region_map = {
            '1': "Total Nacional",
            '2': "Región GBA",
            '3': "Región Pampeana",
            '4': "Región Noroeste",
            '5': "Región Noreste",
            '6': "Región Cuyo",
            '7': "Región Patagonia"
        }
        
        selected_region = region_map.get(region_choice)
        
        if selected_region:
            print(f"\nCargando datos para '{selected_region}' desde Excel...")
            dataset_excel.cargar_datos(selected_region)
            df_ipc = dataset_excel.datos
            source_name = f"Variación Mensual (Excel) - {selected_region}"
            ipc_value_column_name = 'ipc_valor' 
        else:
            print("Opción de región no válida. Saliendo.")
            return
    else:
        print("Opción de fuente de datos no válida. Saliendo.")
        return

    if df_ipc is None or df_ipc.empty:
        print("No se pudieron cargar los datos de IPC desde la fuente seleccionada. No se puede continuar.")
        return

    # --- Análisis de Sueldo vs. Inflación (ingreso directo y cálculo para ese período) ---
    print("\n--- Análisis de Sueldo vs. Inflación ---")
    print("Por favor, ingrese los detalles de su sueldo para la comparación.")
    print("Formato de fecha: AAAA-MM (ej. 2023-01)")

    try:
        sueldo_inicial = float(input("Ingrese su sueldo inicial: $"))
        fecha_sueldo_inicial_str = input("Ingrese la fecha de su sueldo inicial (AAAA-MM): ")
        
        sueldo_final = float(input("Ingrese su sueldo final: $"))
        fecha_sueldo_final_str = input("Ingrese la fecha de su sueldo final (AAAA-MM): ")

        # Convertir a objetos datetime.datetime (la fecha será siempre el primer día del mes)
        fecha_sueldo_inicial = datetime.strptime(fecha_sueldo_inicial_str, '%Y-%m')
        fecha_sueldo_final = datetime.strptime(fecha_sueldo_final_str, '%Y-%m')

        print(f"\nSueldo inicial: ${sueldo_inicial:.2f} (correspondiente a {fecha_sueldo_inicial_str})")
        print(f"Sueldo final:   ${sueldo_final:.2f} (correspondiente a {fecha_sueldo_final_str})")

        # Calcular la inflación acumulada para el PERÍODO DE LOS SUELDOS
        inflacion_acumulada_sueldo_periodo = calcular_inflacion_periodo(
            df_ipc, fecha_sueldo_inicial, fecha_sueldo_final, ipc_value_column_name
        )

        if inflacion_acumulada_sueldo_periodo is not None:
            print(f"Inflación acumulada entre {fecha_sueldo_inicial_str} y {fecha_sueldo_final_str}: {inflacion_acumulada_sueldo_periodo:.2f}%")
        else:
            print(f"No se pudo calcular la inflación para el período de sueldos ({fecha_sueldo_inicial_str} a {fecha_sueldo_final_str}). Asegúrese de que las fechas estén dentro del rango de datos cargados.")
            # Si no se puede calcular la inflación, no tiene sentido continuar con la comparación
            return


        # Calcular el incremento salarial
        if sueldo_inicial != 0:
            incremento_salarial = ((sueldo_final - sueldo_inicial) / sueldo_inicial) * 100
            print(f"Incremento salarial en el período: {incremento_salarial:.2f}%")
        else:
            print("Advertencia: Sueldo inicial es cero, no se puede calcular el incremento salarial.")
            incremento_salarial = 0
            
        # Comparar y mostrar el resultado
        if incremento_salarial > inflacion_acumulada_sueldo_periodo:
            print("\n¡Felicitaciones! Tu sueldo le ganó a la inflación en este período. 🎉")
            diferencia = incremento_salarial - inflacion_acumulada_sueldo_periodo
            print(f"Le ganó por un {diferencia:.2f} puntos porcentuales.")
        elif incremento_salarial < inflacion_acumulada_sueldo_periodo:
            print("\nLamentablemente, tu sueldo perdió contra la inflación en este período. 📉")
            diferencia = inflacion_acumulada_sueldo_periodo - incremento_salarial
            print(f"Perdió por un {diferencia:.2f} puntos porcentuales.")
        else:
            print("\nTu sueldo se mantuvo a la par de la inflación en este período. ⚖️")

        # Opcional: Calcular el poder adquisitivo real
        # Para esto necesitamos los IPCs específicos.
        # Aquí re-usamos la lógica de calcular_inflacion_periodo para obtener los IPCs de los extremos
        # Esto es un poco redundante, pero claro.
        
        # Obtenemos los IPCs para las fechas exactas de sueldo (primer día del mes)
        # Esto debería funcionar ya que el índice del DataFrame es DatetimeIndex con el primer día.
        ipc_inicio_sueldo = df_ipc.loc[fecha_sueldo_inicial.strftime('%Y-%m-%d'), ipc_value_column_name]
        ipc_final_sueldo = df_ipc.loc[fecha_sueldo_final.strftime('%Y-%m-%d'), ipc_value_column_name]

        if ipc_inicio_sueldo != 0:
            sueldo_real_ajustado = sueldo_final / (ipc_final_sueldo / ipc_inicio_sueldo)
            print(f"El poder adquisitivo de tu sueldo final (${sueldo_final:.2f}) es equivalente a ${sueldo_real_ajustado:.2f} en pesos de la fecha inicial.")

    except ValueError:
        print("Entrada inválida. Asegúrate de ingresar números para los sueldos y fechas en formato AAAA-MM.")
    except KeyError as ke:
        print(f"Error al obtener IPC para las fechas del sueldo. Asegúrate que las fechas estén en el rango de datos y que la columna '{ipc_value_column_name}' exista. Detalle: {ke}")
    except Exception as e:
        print(f"Ocurrió un error inesperado durante el análisis de sueldo vs. inflación: {e}")


    # --- Guardar datos en la base de datos (al final de la ejecución principal) ---
    try:
        # Solo guarda si se cargaron datos exitosamente
        if df_ipc is not None and not df_ipc.empty:
            db = DataSaver()
            # Se recomienda un nombre de tabla dinámico o que refleje la fuente de datos
            table_name = "ipc_datos_" + source_name.replace(" ", "_").replace("(", "").replace(")", "").lower()
            db.guardar_dataframe(df_ipc, table_name)
            print(f"\nDatos del IPC ({source_name}) guardados en la tabla '{table_name}' de la base de datos.")
        else:
            print("\nNo hay datos de IPC cargados para guardar.")
    except NameError:
        print("\nAdvertencia: La clase DataSaver no está definida o importada. No se guardarán los datos.")
    except Exception as e:
        print(f"Error al guardar datos con DataSaver: {e}")

if __name__ == "__main__":
    main()