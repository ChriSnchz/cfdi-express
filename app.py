import base64
import datetime
import os
import time
import streamlit as st
from cfdiclient import (Autenticacion, DescargaMasiva, Fiel, SolicitaDescarga,
                        VerificaSolicitudDescarga)

# Variables iniciales
st.title('Descarga Masiva de CFDIs')
RFC = st.text_input("Ingresa tu RFC", placeholder='RFC').upper()
FIEL_CER = st.file_uploader("Selecciona tu archivo .cer", type=["cer"])
FIEL_KEY = st.file_uploader("Selecciona tu archivo .key", type=["key"])
FIEL_PAS = st.text_input('Contraseña de la FIEL', type='password')
FECHA_INICIAL = st.date_input('Fecha Inicial')
FECHA_FINAL = st.date_input('Fecha Final')

if st.button('Iniciar Descarga'):
    try:

        if FIEL_CER and FIEL_KEY and FIEL_PAS:
            # Guardar los archivos subidos
            with open("temp.cer", "wb") as f:
                f.write(FIEL_CER.getbuffer())
            with open("temp.key", "wb") as f:
                f.write(FIEL_KEY.getbuffer())


        cer_der = open("temp.cer", "rb").read()
        key_der = open("temp.key", "rb").read()

        fiel = Fiel(cer_der, key_der, FIEL_PAS)
        auth = Autenticacion(fiel)
        token = auth.obtener_token()

        #st.write(f'TOKEN: {token}')

        descarga = SolicitaDescarga(fiel)

        # Tipo de solicitud
        tipo_solicitud = st.radio('Selecciona el tipo de solicitud', ['Emitidos', 'Recibidos'])

        if tipo_solicitud == 'Emitidos':
            solicitud = descarga.solicitar_descarga(
                token, RFC, FECHA_INICIAL, FECHA_FINAL, rfc_emisor=RFC, tipo_solicitud='CFDI'
            )
        else:
            solicitud = descarga.solicitar_descarga(
                token, RFC, FECHA_INICIAL, FECHA_FINAL, rfc_receptor=RFC, tipo_solicitud='CFDI'
            )

        st.write(f'SOLICITUD: {solicitud}')

        with st.spinner('Verificando estado de la solicitud...'):
            while True:
                token = auth.obtener_token()
                verificacion = VerificaSolicitudDescarga(fiel)
                verificacion = verificacion.verificar_descarga(token, RFC, solicitud['id_solicitud'])

                st.write(f'Estado de Solicitud: {verificacion["estado_solicitud"]}')

                estado_solicitud = int(verificacion['estado_solicitud'])

                if estado_solicitud <= 2:
                    # Estado aceptado o en proceso, esperar 60 segundos
                    time.sleep(60)
                    continue
                elif estado_solicitud >= 4:
                    st.error(f'Error en la solicitud: {estado_solicitud}')
                    break
                else:
                    # Descargar los paquetes si el estado es 3 (Terminada)
                    for paquete in verificacion['paquetes']:
                        descarga = DescargaMasiva(fiel)
                        descarga = descarga.descargar_paquete(token, RFC, paquete)
                        st.write(f'Descargando paquete: {paquete}')
                        with open(f'{paquete}.zip', 'wb') as fp:
                            fp.write(base64.b64decode(descarga['paquete_b64']))
                    st.success('Descarga completada')
                    break
    except Exception as e:
        st.error(f'Error: {e}')
