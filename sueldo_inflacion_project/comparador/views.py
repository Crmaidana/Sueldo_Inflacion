# comparador/views.py
import pandas as pd
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import HttpResponse

# Importa tus clases de lógica de negocio (asumiendo que las clases en domain/ ya están como las pasaste)
from comparador.domain.dataset_api import DatasetAPI
from comparador.domain.dataset_csv import DatasetCsv
from comparador.domain.dataset_excel import DatasetExcel
# from comparador.data.data_saver import DataSaver # Asegúrate de tener esta clase implementada si la usas

# La función calcular_inflacion_periodo: Aquí está el cambio clave para el cálculo.
def calcular_inflacion_periodo(df, fecha_inicio_raw_form, fecha_fin_raw_form, valor_columna='ipc_valor'):
    """
    Calcula la inflación acumulada para un período dado (ej. de Enero a Mayo).
    Requiere un DataFrame con índice de fechas y una columna de valor (ej. 'ipc_valor').
    
    Args:
        df (pd.DataFrame): DataFrame de IPC con DatetimeIndex y la columna de valores.
        fecha_inicio_raw_form (datetime): Fecha de inicio del período deseado (ej. datetime(2025,1,1) para Enero 2025).
        fecha_fin_raw_form (datetime): Fecha de fin del período deseado (ej. datetime(2025,5,1) para Mayo 2025).
        valor_columna (str): Nombre de la columna que contiene los valores del IPC.
    
    Returns:
        float: La inflación acumulada en porcentaje.
        None: Si no se puede calcular.
    """
    try:
        # Asegurarse de que el DataFrame sea válido
        if df is None or df.empty or valor_columna not in df.columns:
            print(f"Error: DataFrame inválido o columna '{valor_columna}' no encontrada para el cálculo de inflación.")
            return None

        # Asegurarse de que el índice sea DatetimeIndex y esté ordenado
        # Si no lo es, intenta convertirlo.
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'fecha' in df.columns: # Si 'fecha' es una columna, usarla para el índice
                df['fecha'] = pd.to_datetime(df['fecha'])
                df = df.set_index('fecha')
            else:
                # Si no hay 'fecha' y el índice no es DatetimeIndex, es un problema.
                print("Error: El DataFrame no tiene un índice de fecha ni una columna 'fecha' para el cálculo.")
                return None

        df.sort_index(inplace=True)
        # Convertir el índice a fin de mes para asegurar la consistencia con asof()
        # Es posible que ya lo haga transformar_datos de la clase base Dataset (si la usas),
        # pero es una buena práctica defensiva asegurar esto aquí.
        df.index = df.index.to_period('M').to_timestamp('M')

        # --- Determinación de las fechas de IPC para el cálculo ---
        # Para inflación "de Enero a Mayo", necesitamos:
        # - IPC de Diciembre del año anterior (como base)
        # - IPC de Mayo del año actual (como final)

        # Fecha de fin para el IPC final (ej. 2025-05-31 para Mayo 2025)
        fecha_fin_ipc = fecha_fin_raw_form + pd.offsets.MonthEnd(0)

        # Fecha de inicio para el IPC base (ej. 2024-12-31 para Diciembre 2024)
        fecha_inicio_ipc_base = fecha_inicio_raw_form + pd.offsets.MonthEnd(0) - pd.DateOffset(months=1)

        print(f"DEBUG: Buscando IPC para base en {fecha_inicio_ipc_base.strftime('%Y-%m-%d')} y final en {fecha_fin_ipc.strftime('%Y-%m-%d')}")

        # Buscar el valor de IPC para la fecha de inicio de la base
        # Usamos .asof() para encontrar el último valor en o antes de la fecha.
        ipc_inicio_series = df[valor_columna].asof(fecha_inicio_ipc_base)
        if pd.isna(ipc_inicio_series):
            # Contingencia: si asof no encuentra un valor exacto, buscar el primer valor >= fecha_inicio
            try:
                idx_ge_start = df.index[df.index >= fecha_inicio_ipc_base].min()
                ipc_inicio = df.loc[idx_ge_start, valor_columna]
                print(f"DEBUG: IPC base (>=) para fecha {fecha_inicio_ipc_base.strftime('%Y-%m-%d')} encontrado en {idx_ge_start.strftime('%Y-%m-%d')}: {ipc_inicio:.2f}")
            except ValueError:
                print(f"Error: No se encontró IPC para el mes de inicio del período de base: {fecha_inicio_ipc_base.strftime('%Y-%m')}. Revise el rango de datos.")
                return None
        else:
            ipc_inicio = ipc_inicio_series
            print(f"DEBUG: IPC base (asof) para fecha {fecha_inicio_ipc_base.strftime('%Y-%m-%d')}: {ipc_inicio:.2f}")

        # Buscar el valor de IPC para la fecha de fin del período
        ipc_fin_series = df[valor_columna].asof(fecha_fin_ipc)
        if pd.isna(ipc_fin_series):
            # Contingencia: si asof no encuentra un valor exacto, buscar el último valor <= fecha_fin
            try:
                idx_le_end = df.index[df.index <= fecha_fin_ipc].max()
                ipc_fin = df.loc[idx_le_end, valor_columna]
                print(f"DEBUG: IPC final (<=) para fecha {fecha_fin_ipc.strftime('%Y-%m-%d')} encontrado en {idx_le_end.strftime('%Y-%m-%d')}: {ipc_fin:.2f}")
            except ValueError:
                print(f"Error: No se encontró IPC para el mes de fin del período: {fecha_fin_ipc.strftime('%Y-%m')}. Revise el rango de datos.")
                return None
        else:
            ipc_fin = ipc_fin_series
            print(f"DEBUG: IPC final (asof) para fecha {fecha_fin_ipc.strftime('%Y-%m-%d')}: {ipc_fin:.2f}")

        if ipc_inicio is None or ipc_fin is None or ipc_inicio == 0:
            print("Error: Valores de IPC inicial o final inválidos (cero o None). No se puede calcular la inflación.")
            return None

        # Calcular la inflación porcentual utilizando la fórmula de encadenamiento
        inflacion_porcentual = ((ipc_fin / ipc_inicio) - 1) * 100
        return inflacion_porcentual
    
    except Exception as e:
        print(f"Error general al calcular la inflación del período en calcular_inflacion_periodo: {e}")
        return None


def index(request):
    df_ipc = pd.DataFrame()
    source_name = ""
    ipc_value_column_name = None # El nombre de la columna del IPC puede variar según la fuente
    result = None
    error_message = None

    if request.method == 'POST':
        # Recuperar datos del formulario
        choice_source = request.POST.get('source_choice')
        region_choice = request.POST.get('region_choice') # Solo relevante para Excel
        sueldo_inicial_str = request.POST.get('sueldo_inicial')
        fecha_sueldo_inicial_str = request.POST.get('fecha_sueldo_inicial') # Formato AAAA-MM
        sueldo_final_str = request.POST.get('sueldo_final')
        fecha_sueldo_final_str = request.POST.get('fecha_sueldo_final') # Formato AAAA-MM

        # Validación básica de entradas
        try:
            sueldo_inicial = float(sueldo_inicial_str)
            sueldo_final = float(sueldo_final_str)
            # Parsear las fechas a datetime objects (primer día del mes)
            fecha_sueldo_inicial = datetime.strptime(fecha_sueldo_inicial_str, '%Y-%m')
            fecha_sueldo_final = datetime.strptime(fecha_sueldo_final_str, '%Y-%m')
        except (ValueError, TypeError):
            error_message = "Por favor, ingrese valores numéricos válidos para los sueldos y fechas en formato AAAA-MM."
            return render(request, 'comparador/index.html', {'error_message': error_message})

        # Rutas de los archivos de datos (ajusta si es necesario, ahora son relativas a la app)
        csv_file_path = 'comparador/file/ipc-chaco-historico.csv'
        excel_file_path = 'comparador/file/sh_ipc_07_25.xls' # O sh_ipc_05_25.xls según el que uses

        # Instanciar los datasets
        dataset_api_indec = DatasetAPI() # Se mantiene la inicialización original
        dataset_csv = DatasetCsv(csv_file_path) # Se mantiene la inicialización original
        dataset_excel = DatasetExcel(excel_file_path) # Se mantiene la inicialización original

        # --- Selección y carga de la fuente de datos ---
        try:
            if choice_source == '1': # INDEC API
                source_name = "INDEC (API)"
                # Calcular un rango de fechas amplio para la API para asegurar que los datos estén disponibles.
                # Se utiliza el IPC_NATIONAL_ID de la clase DatasetAPI directamente.
                api_start_date_obj = fecha_sueldo_inicial.replace(day=1).replace(year=fecha_sueldo_inicial.year - 1)
                api_end_date_obj = fecha_sueldo_final.replace(day=1) + pd.DateOffset(months=1)
                
                # Asegurarse de que la fecha de inicio de la API no sea antes de la base del IPC (ej. Dic 2016)
                if api_start_date_obj < datetime(2016, 12, 1):
                    api_start_date_obj = datetime(2016, 12, 1)

                # Se llama a cargar_datos de DatasetAPI con sus argumentos específicos (series_ids, start_date, end_date)
                dataset_api_indec.cargar_datos(series_ids=[dataset_api_indec.IPC_NATIONAL_ID],
                                               start_date=api_start_date_obj.strftime('%Y-%m-%d'),
                                               end_date=api_end_date_obj.strftime('%Y-%m-%d'))
                df_ipc = dataset_api_indec.datos
                # El nombre de la columna para la API es su IPC_NATIONAL_ID, asumimos que DatasetAPI lo expone así.
                ipc_value_column_name = dataset_api_indec.IPC_NATIONAL_ID 

            elif choice_source == '2': # CSV
                source_name = "IPC Chaco (CSV)"
                # Se llama a cargar_datos de DatasetCsv sin argumentos adicionales, como en tu código original.
                dataset_csv.cargar_datos() 
                df_ipc = dataset_csv.datos # Acceder via propiedad .datos
                # El nombre de la columna esperado del CSV es 'ipc_valor'.
                ipc_value_column_name = 'ipc_valor' 

            elif choice_source == '3': # Excel
                region_map = {
                    '1': "Total Nacional", '2': "Región GBA", '3': "Región Pampeana",
                    '4': "Región Noroeste", '5': "Región Noreste", '6': "Región Cuyo",
                    '7': "Región Patagonia"
                }
                selected_region = region_map.get(region_choice)
                if not selected_region:
                    raise ValueError("Opción de región no válida para Excel.")
                
                source_name = f"Variación Mensual (Excel) - {selected_region}"
                # Se llama a cargar_datos de DatasetExcel con el argumento region_name, como en tu código original.
                dataset_excel.cargar_datos(selected_region)
                df_ipc = dataset_excel.datos # Acceder via propiedad .datos
                # El nombre de la columna esperado del Excel es 'ipc_valor'.
                ipc_value_column_name = 'ipc_valor' 

            else:
                raise ValueError("Opción de fuente de datos no válida.")

            # Validación final del DataFrame después de la carga
            if df_ipc is None or df_ipc.empty:
                raise ValueError("No se pudieron cargar los datos de IPC desde la fuente seleccionada. No se puede continuar.")

        except Exception as e:
            error_message = f"Error al cargar datos desde la fuente seleccionada: {e}"
            return render(request, 'comparador/index.html', {'error_message': error_message})

        # --- Análisis de Sueldo vs. Inflación ---
        # Llamar a la función que calcula la inflación acumulada con las fechas y columna correctas.
        inflacion_acumulada_sueldo_periodo = calcular_inflacion_periodo(
            df_ipc, fecha_sueldo_inicial, fecha_sueldo_final, ipc_value_column_name
        )

        if inflacion_acumulada_sueldo_periodo is not None:
            if sueldo_inicial != 0:
                incremento_salarial = ((sueldo_final - sueldo_inicial) / sueldo_inicial) * 100
            else:
                incremento_salarial = 0
                error_message = "Advertencia: Sueldo inicial es cero, no se puede calcular el incremento salarial."

            # Comparar y preparar el resultado
            if incremento_salarial > inflacion_acumulada_sueldo_periodo:
                diferencia = incremento_salarial - inflacion_acumulada_sueldo_periodo
                resultado_texto = f"¡Felicitaciones! Tu sueldo le ganó a la inflación en este período. 🎉 Le ganó por un {diferencia:.2f} puntos porcentuales."
                clase_resultado = "resultado-ganado"
            elif incremento_salarial < inflacion_acumulada_sueldo_periodo:
                diferencia = inflacion_acumulada_sueldo_periodo - incremento_salarial
                resultado_texto = f"Lamentablemente, tu sueldo perdió contra la inflación en este período. 📉 Perdió por un {diferencia:.2f} puntos porcentuales."
                clase_resultado = "resultado-perdido"
            else:
                resultado_texto = "Tu sueldo se mantuvo a la par de la inflación en este período. ⚖️"
                clase_resultado = "resultado-neutro"

            # Poder adquisitivo real
            try:
                # Las fechas para obtener el poder adquisitivo se refieren a los meses de los sueldos
                # Se busca el IPC de fin de mes para las fechas de sueldo_inicial y sueldo_final.
                # Aseguramos que el df_ipc.index sea DatetimeIndex y que esté en fin de mes al inicio de la función.
                
                # Ajusta las fechas de sueldo a fin de mes para la búsqueda en el DataFrame
                fecha_sueldo_inicial_adj = fecha_sueldo_inicial + pd.offsets.MonthEnd(0)
                fecha_sueldo_final_adj = fecha_sueldo_final + pd.offsets.MonthEnd(0)

                # Usar asof() para buscar el IPC más cercano o exacto
                ipc_inicio_sueldo_series = df_ipc[ipc_value_column_name].asof(fecha_sueldo_inicial_adj)
                ipc_final_sueldo_series = df_ipc[ipc_value_column_name].asof(fecha_sueldo_final_adj)

                if pd.isna(ipc_inicio_sueldo_series) or pd.isna(ipc_final_sueldo_series) or ipc_inicio_sueldo_series == 0:
                    poder_adquisitivo_texto = "No se pudo calcular el poder adquisitivo real (IPC no disponible para las fechas de sueldo o IPC inicial es cero)."
                else:
                    ipc_inicio_sueldo = ipc_inicio_sueldo_series
                    ipc_final_sueldo = ipc_final_sueldo_series
                    sueldo_real_ajustado = sueldo_final / (ipc_final_sueldo / ipc_inicio_sueldo)
                    poder_adquisitivo_texto = f"El poder adquisitivo de tu sueldo final (${sueldo_final:.2f}) es equivalente a ${sueldo_real_ajustado:.2f} en pesos de la fecha inicial."
            except Exception as e:
                poder_adquisitivo_texto = f"Ocurrió un error al calcular el poder adquisitivo: {e}"

            result = {
                'sueldo_inicial': sueldo_inicial,
                'fecha_sueldo_inicial': fecha_sueldo_inicial_str,
                'sueldo_final': sueldo_final,
                'fecha_sueldo_final': fecha_sueldo_final_str,
                'inflacion_acumulada': f"{inflacion_acumulada_sueldo_periodo:.2f}%",
                'incremento_salarial': f"{incremento_salarial:.2f}%",
                'resultado_texto': resultado_texto,
                'clase_resultado': clase_resultado,
                'poder_adquisitivo_texto': poder_adquisitivo_texto,
                'source_name': source_name,
            }
        else:
            error_message = f"No se pudo calcular la inflación para el período de sueldos ({fecha_sueldo_inicial_str} a {fecha_sueldo_final_str}). Asegúrese de que las fechas estén dentro del rango de datos cargados y que los datos sean válidos."

        # --- Guardar datos en la base de datos (opcional, considera si es necesario aquí) ---
        # Este bloque se mantiene como lo tenías. Si DataSaver no existe o no se usa, puedes dejarlo comentado.
        if df_ipc is not None and not df_ipc.empty and not error_message:
            try:
                # db = DataSaver()
                # table_name = "ipc_datos_" + source_name.replace(" ", "_").replace("(", "").replace(")", "").lower()
                # db.guardar_dataframe(df_ipc, table_name)
                # print(f"Datos del IPC ({source_name}) guardados en la tabla '{table_name}'.")
                pass # Eliminé el código comentado para evitar errores si DataSaver no está implementado
            except NameError:
                print("Advertencia: La clase DataSaver no está definida o importada. No se guardarán los datos.")
            except Exception as e:
                print(f"Error al guardar datos con DataSaver: {e}")

    # Renderizar la plantilla con los resultados o el formulario vacío
    context = {
        'result': result,
        'error_message': error_message,
    }
    return render(request, 'comparador/index.html', context)
