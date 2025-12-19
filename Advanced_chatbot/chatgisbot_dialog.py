import requests
from qgis.PyQt import QtWidgets
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsDataSourceUri,
    QgsProviderRegistry
)


class ChatGISBotDialog(QtWidgets.QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface

        self.setWindowTitle("ChatGISBot")
        self.resize(520, 380)

        self.input = QtWidgets.QTextEdit()
        self.input.setPlaceholderText("Enter a spatial query...")

        self.run_button = QtWidgets.QPushButton("Run")

        self.output = QtWidgets.QTextEdit()
        self.output.setReadOnly(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.input)
        layout.addWidget(self.run_button)
        layout.addWidget(self.output)

        self.run_button.clicked.connect(self.run_query)

    def _get_active_postgis_layer(self):
        """
        Returns the currently active PostGIS vector layer.
        """
        layer = self.iface.activeLayer()
        if not layer:
            return None, "Please select a layer first."

        if not isinstance(layer, QgsVectorLayer) or layer.providerType() != "postgres":
            return None, "The active layer must be a PostGIS vector layer."

        return layer, None

    def run_query(self):
        """
        Sends a natural language query to the API,
        executes the returned SQL, and loads the result layer.
        """
        question = self.input.toPlainText().strip()
        if not question:
            return

        layer, error = self._get_active_postgis_layer()
        if error:
            QtWidgets.QMessageBox.warning(self, "ChatGISBot", error)
            return

        uri = QgsDataSourceUri(layer.source())
        schema = uri.schema() or "public"
        table = uri.table()
        geom_column = uri.geometryColumn() or "geom"

        if not table:
            QtWidgets.QMessageBox.warning(
                self,
                "ChatGISBot",
                "Unable to determine the table name from the active layer."
            )
            return

        # Send request to the NL2SQL API
        try:
            response = requests.post(
                "http://127.0.0.1:8000/nl2sql",
                json={
                    "question": question,
                    "schema": schema,
                    "table": table,
                    "geom": geom_column
                },
                timeout=300
            )
            response.raise_for_status()
            sql = response.json().get("sql", "").strip()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "ChatGISBot",
                f"Failed to connect to the API server:\n{e}"
            )
            return

        if not sql.lower().startswith("create table"):
            QtWidgets.QMessageBox.critical(
                self,
                "ChatGISBot",
                "The server returned an invalid SQL statement."
            )
            self.output.setPlainText(sql)
            return

        self.output.setPlainText(sql)

        # Execute SQL using the same database connection
        try:
            metadata = QgsProviderRegistry.instance().providerMetadata("postgres")
            connection = metadata.createConnection(uri.uri(False), {})

            connection.executeSql("DROP TABLE IF EXISTS public.analysis_result;")
            connection.executeSql(sql)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "ChatGISBot",
                f"Error while executing SQL:\n{e}"
            )
            return

        # Load result as a new layer
        try:
            result_uri = QgsDataSourceUri(uri.uri(False))
            result_uri.setDataSource("public", "analysis_result", "geom")

            result_layer = QgsVectorLayer(
                result_uri.uri(False),
                "AI Result",
                "postgres"
            )

            if not result_layer.isValid():
                QtWidgets.QMessageBox.critical(
                    self,
                    "ChatGISBot",
                    "The result table was created, but the layer could not be loaded."
                )
                return

            QgsProject.instance().addMapLayer(result_layer)
            self.iface.setActiveLayer(result_layer)
            self.iface.zoomToActiveLayer()

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "ChatGISBot",
                f"Error while loading the result layer:\n{e}"
            )
