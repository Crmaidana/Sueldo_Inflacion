import pandas as pd
from datetime import datetime, timedelta

from domain.dataset_api import DatasetAPI
from domain.dataset_csv import DatasetCsv
from domain.dataset_excel import DatasetExcel

# La función calcular_inflacion_periodo es genérica y puede quedarse
def calcular_inflacion_periodo(df, fecha_inicio, fecha_fin, valor_columna='ipc_valor'):
    """
    Calcula la inflación acumulada para un período dado.
    Requiere un DataFrame con índice de fechas y una columna de valor (por defecto 'ipc_valor').
    """
    try:
        # Asegurarse de que el índice sea DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            print("Advertencia: El DataFrame no tiene un DatetimeIndex. Intentando convertir 'fecha' a índice.")
            if 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha'])
                df = df.set_index('fecha')
            else:
                raise ValueError("El DataFrame no tiene un índice de fecha ni una columna 'fecha'.")
        
        # Ajustar fecha_fin para incluir todo el mes si el índice es el primer día del mes
        # Esto asegura que df.loc[fecha_inicio:fecha_fin] incluya el mes de fin
        # Si el índice es el 1 del mes, entonces un slice a '2025-04-01' incluirá los datos de abril.
        
        df_periodo = df.loc[fecha_inicio.strftime('%Y-%m'):fecha_fin.strftime('%Y-%m')]

        if df_periodo.empty:
            print(f"No hay datos disponibles para el período {fecha_inicio.strftime('%Y-%m')} a {fecha_fin.strftime('%Y-%m')}.")
            return None

        # Obtener el IPC al inicio y al final del período
        # Usamos .iloc[0] y .iloc[-1] para asegurar que tomamos el primer y último valor del periodo filtrado.
        ipc_inicio = df_periodo[valor_columna].iloc[0]
        ipc_fin = df_periodo[valor_columna].iloc[-1]

        # Calcular la inflación porcentual
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
    # Usamos DatasetAPIi como en tu main original
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
        # Lógica para definir fechas de inicio y fin de la API (tomada de tu main original)
        current_date = datetime.now()
        if current_date.month <= 2: 
            end_date_obj_api = current_date.replace(year=current_date.year - 1, month=current_date.month + 12 - 2, day=1)
        else:
            end_date_obj_api = current_date.replace(month=current_date.month - 2, day=1)
        end_date_str_api = end_date_obj_api.strftime('%Y-%m-%d')
        start_date_obj_api = end_date_obj_api - timedelta(days=30 * 14)
        start_date_str_api = start_date_obj_api.strftime('%Y-%m-%d')

        print(f"Período de consulta para el IPC (API INDEC): desde {start_date_str_api} hasta {end_date_str_api}")

        try:
            # Llamamos a cargar_datos con los parámetros que DatasetAPIi espera
            dataset_api_indec.cargar_datos(series_ids=[dataset_api_indec.IPC_NATIONAL_ID],
                                        start_date=start_date_str_api,
                                        end_date=end_date_str_api)

            df_ipc = dataset_api_indec.datos # <-- Accediendo a la propiedad 'datos' directamente
            source_name = "INDEC (API)"
            # La columna de valor para el INDEC será el ID de la serie
            ipc_value_column_name = dataset_api_indec.IPC_NATIONAL_ID 
            
            if df_ipc is not None and not df_ipc.empty:
                # Asegurarse de que el índice sea de fecha para el cálculo posterior
                if 'fecha' in df_ipc.columns:
                    df_ipc.set_index('fecha', inplace=True)
                df_ipc.sort_index(inplace=True)
                print("Datos de IPC INDEC cargados exitosamente.")
                # print(df_ipc.head()) # Para depuración
            else:
                print("No se pudieron obtener datos del IPC del INDEC.")

        except Exception as e:
            print(f"Error al cargar datos del INDEC: {e}")

    elif choice_source == '2':
        print("\nCargando datos históricos de IPC Chaco (CSV)...")
        dataset_csv.cargar_datos()
        df_ipc = dataset_csv.obtener_datos()
        source_name = "IPC Chaco (CSV)"
        # La columna de valor para CSV es 'ipc_valor' (asumiendo que es así en tu clase)
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
            # Aquí, la lógica en DatasetExcel.cargar_datos(region) debe calcular el IPC acumulado
            # y devolver un DataFrame con un índice de fecha y una columna 'ipc_valor' o similar.
            dataset_excel.cargar_datos(selected_region)
            df_ipc = dataset_excel.datos
            source_name = f"Variación Mensual (Excel) - {selected_region}"
            # Asumimos que Excel también produce una columna 'ipc_valor'
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

    # --- Solicitud de período al usuario para el cálculo de inflación ---
    print("\nIngrese el período para el cual desea calcular la inflación.")
    print("Formato de fecha: AAAA-MM (ej. 2023-01)")

    fecha_inicio_str = input("Fecha de inicio (AAAA-MM): ")
    fecha_fin_str = input("Fecha de fin (AAAA-MM): ")

    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m')
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m')
        
        # Pasar el nombre de la columna que contiene los valores IPC
        inflacion = calcular_inflacion_periodo(df_ipc, fecha_inicio, fecha_fin, ipc_value_column_name)

        if inflacion is not None:
            print(f"\n--- Resultado del Cálculo de Inflación ---")
            print(f"Fuente de Datos: {source_name}")
            print(f"Período: {fecha_inicio_str} a {fecha_fin_str}")
            print(f"Inflación Acumulada: {inflacion:.2f}%")
        else:
            print("\nNo se pudo calcular la inflación para el período y fuente de datos seleccionados.")

    except ValueError:
        print("Formato de fecha inválido. Por favor, use AAAA-MM.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    main()