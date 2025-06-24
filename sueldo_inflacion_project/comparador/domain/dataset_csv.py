# domain/dataset_csv.py
import pandas as pd
# Antes:
# from domain.dataset import Dataset
# Después:
from .dataset import Dataset # <-- Cambio aquí

class DatasetCsv(Dataset):
    def __init__(self, file_path):
        self.file_path = file_path
        self.datos = pd.DataFrame()

    def cargar_datos(self):
        """
        Carga los datos de IPC desde el archivo CSV.
        """
        try:
            # Columnas exactas del CSV según la información del usuario
            date_col = 'indice_tiempo'
            ipc_col = 'ipc_chaco_historico_ng'

            self.datos = pd.read_csv(self.file_path)

            # Asegurarse de que las columnas existen
            if date_col not in self.datos.columns:
                print(f"Error: Columna de fecha '{date_col}' no encontrada en el CSV.")
                self.datos = pd.DataFrame() # Vaciar datos si hay error
                return
            if ipc_col not in self.datos.columns:
                print(f"Error: Columna de IPC '{ipc_col}' no encontrada en el CSV.")
                self.datos = pd.DataFrame() # Vaciar datos si hay error
                return

            self.datos['fecha'] = pd.to_datetime(self.datos[date_col])
            self.datos['ipc_valor'] = pd.to_numeric(self.datos[ipc_col], errors='coerce') # Convertir a numérico, errores a NaN

            # Eliminar filas con valores NaN en ipc_valor si los hay
            self.datos.dropna(subset=['ipc_valor'], inplace=True)

            self.datos.set_index('fecha', inplace=True)
            self.datos.sort_index(inplace=True)

            # Seleccionar solo las columnas relevantes
            self.datos = self.datos[['ipc_valor']]

            print(f"Datos de IPC para Chaco cargados exitosamente desde CSV.")

        except FileNotFoundError:
            print(f"Error: Archivo CSV no encontrado en la ruta {self.file_path}")
        except Exception as e:
            print(f"Error al cargar datos desde CSV: {e}")

    def obtener_datos(self):
        return self.datos