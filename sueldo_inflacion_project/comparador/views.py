# comparador/views.py
import pandas as pd
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import HttpResponse # Para respuestas simples, aunque usaremos render

# Importa tus clases de lógica de negocio
from comparador.domain.dataset_api import DatasetAPI
from comparador.domain.dataset_csv import DatasetCsv
from comparador.domain.dataset_excel import DatasetExcel
from comparador.data.data_saver import DataSaver # Asegúrate de tener esta clase implementada

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

        # Convertir las fechas de inicio y fin a string 'YYYY-MM-DD' para usar con .loc
        fecha_inicio_str_month = fecha_inicio.strftime('%Y-%m-%d')
        fecha_fin_str_month = fecha_fin.strftime('%Y-%m-%d')

        # Buscar el valor de IPC para la fecha de inicio del período
        try:
            ipc_inicio = df.loc[fecha_inicio_str_month, valor_columna]
        except KeyError:
            ipc_inicio_series = df.loc[df.index.to_period('M') == fecha_inicio.to_period('M'), valor_columna]
            if ipc_inicio_series.empty:
                # Aquí podrías loggear un error en lugar de imprimirlo directamente
                print(f"Error: No se encontró IPC para el mes de inicio del período: {fecha_inicio.strftime('%Y-%m')}. Revise el rango de datos.")
                return None
            ipc_inicio = ipc_inicio_series.iloc[0]

        try:
            ipc_fin = df.loc[fecha_fin_str_month, valor_columna]
        except KeyError:
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


def index(request):
    # Esta vista manejará tanto la visualización del formulario como el procesamiento de los datos
    df_ipc = pd.DataFrame()
    source_name = ""
    ipc_value_column_name = 'ipc_valor'
    result = None
    error_message = None

    if request.method == 'POST':
        # Recuperar datos del formulario
        choice_source = request.POST.get('source_choice')
        region_choice = request.POST.get('region_choice') # Solo relevante para Excel
        sueldo_inicial_str = request.POST.get('sueldo_inicial')
        fecha_sueldo_inicial_str = request.POST.get('fecha_sueldo_inicial')
        sueldo_final_str = request.POST.get('sueldo_final')
        fecha_sueldo_final_str = request.POST.get('fecha_sueldo_final')

        # Validación básica de entradas
        try:
            sueldo_inicial = float(sueldo_inicial_str)
            sueldo_final = float(sueldo_final_str)
            fecha_sueldo_inicial = datetime.strptime(fecha_sueldo_inicial_str, '%Y-%m')
            fecha_sueldo_final = datetime.strptime(fecha_sueldo_final_str, '%Y-%m')
        except (ValueError, TypeError):
            error_message = "Por favor, ingrese valores numéricos válidos para los sueldos y fechas en formato AAAA-MM."
            return render(request, 'comparador/index.html', {'error_message': error_message})

        # Rutas de los archivos de datos (ajusta si es necesario, ahora son relativas a la app)
        csv_file_path = 'comparador/file/ipc-chaco-historico.csv'
        excel_file_path = 'comparador/file/sh_ipc_06_25.xls' # O sh_ipc_05_25.xls según el que uses

        # Instanciar los datasets
        dataset_api_indec = DatasetAPI()
        dataset_csv = DatasetCsv(csv_file_path)
        dataset_excel = DatasetExcel(excel_file_path)

        # --- Selección de la fuente de datos ---
        if choice_source == '1': # INDEC API
            current_date = datetime.now()
            end_date_obj_api = current_date.replace(day=1) - timedelta(days=1)
            end_date_obj_api = end_date_obj_api.replace(day=1)
            end_date_str_api = end_date_obj_api.strftime('%Y-%m-%d')
            start_date_obj_api = end_date_obj_api.replace(year=end_date_obj_api.year - 5)
            start_date_str_api = start_date_obj_api.strftime('%Y-%m-%d')

            try:
                dataset_api_indec.cargar_datos(series_ids=[dataset_api_indec.IPC_NATIONAL_ID],
                                            start_date=start_date_str_api,
                                            end_date=end_date_str_api)
                df_ipc = dataset_api_indec.datos
                source_name = "INDEC (API)"
                ipc_value_column_name = dataset_api_indec.IPC_NATIONAL_ID

                if df_ipc is not None and not df_ipc.empty:
                    if 'fecha' in df_ipc.columns:
                        df_ipc.set_index('fecha', inplace=True)
                    df_ipc.sort_index(inplace=True)
                else:
                    error_message = "No se pudieron obtener datos del IPC del INDEC."
            except Exception as e:
                error_message = f"Error al cargar datos del INDEC: {e}"

        elif choice_source == '2': # CSV
            dataset_csv.cargar_datos()
            df_ipc = dataset_csv.obtener_datos()
            source_name = "IPC Chaco (CSV)"
            ipc_value_column_name = 'ipc_valor'

        elif choice_source == '3': # Excel
            region_map = {
                '1': "Total Nacional", '2': "Región GBA", '3': "Región Pampeana",
                '4': "Región Noroeste", '5': "Región Noreste", '6': "Región Cuyo",
                '7': "Región Patagonia"
            }
            selected_region = region_map.get(region_choice)

            if selected_region:
                try:
                    dataset_excel.cargar_datos(selected_region)
                    df_ipc = dataset_excel.datos
                    source_name = f"Variación Mensual (Excel) - {selected_region}"
                    ipc_value_column_name = 'ipc_valor'
                except Exception as e:
                    error_message = f"Error al cargar datos del Excel para {selected_region}: {e}"
            else:
                error_message = "Opción de región no válida."

        else:
            error_message = "Opción de fuente de datos no válida."

        if df_ipc is None or df_ipc.empty:
            error_message = error_message or "No se pudieron cargar los datos de IPC desde la fuente seleccionada. No se puede continuar."
        else:
            # --- Análisis de Sueldo vs. Inflación ---
            inflacion_acumulada_sueldo_periodo = calcular_inflacion_periodo(
                df_ipc, fecha_sueldo_inicial, fecha_sueldo_final, ipc_value_column_name
            )

            if inflacion_acumulada_sueldo_periodo is not None:
                if sueldo_inicial != 0:
                    incremento_salarial = ((sueldo_final - sueldo_inicial) / sueldo_inicial) * 100
                else:
                    incremento_salarial = 0 # No se puede calcular el incremento si el inicial es 0
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
                    ipc_inicio_sueldo = df_ipc.loc[fecha_sueldo_inicial.strftime('%Y-%m-%d'), ipc_value_column_name]
                    ipc_final_sueldo = df_ipc.loc[fecha_sueldo_final.strftime('%Y-%m-%d'), ipc_value_column_name]
                    if ipc_inicio_sueldo != 0:
                        sueldo_real_ajustado = sueldo_final / (ipc_final_sueldo / ipc_inicio_sueldo)
                        poder_adquisitivo_texto = f"El poder adquisitivo de tu sueldo final (${sueldo_final:.2f}) es equivalente a ${sueldo_real_ajustado:.2f} en pesos de la fecha inicial."
                    else:
                        poder_adquisitivo_texto = "No se pudo calcular el poder adquisitivo real (IPC inicial es cero)."
                except KeyError as ke:
                    poder_adquisitivo_texto = f"Error al obtener IPC para las fechas del sueldo. Detalle: {ke}"
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
                error_message = f"No se pudo calcular la inflación para el período de sueldos ({fecha_sueldo_inicial_str} a {fecha_sueldo_final_str}). Asegúrese de que las fechas estén dentro del rango de datos cargados."

        # --- Guardar datos en la base de datos (opcional, considera si es necesario aquí) ---
        # La lógica de guardar en la DB debería ejecutarse si el cálculo fue exitoso
        if df_ipc is not None and not df_ipc.empty and not error_message:
            try:
                db = DataSaver()
                table_name = "ipc_datos_" + source_name.replace(" ", "_").replace("(", "").replace(")", "").lower()
                db.guardar_dataframe(df_ipc, table_name)
                # No es necesario mostrar este mensaje en la interfaz, pero se puede loggear
                print(f"Datos del IPC ({source_name}) guardados en la tabla '{table_name}'.")
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