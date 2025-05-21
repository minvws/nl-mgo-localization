# ZorgAB healtcare provider

In order to use the ZorgAB healthcare provider API, you must do the following:

1. Make sure you have access to the zorgab platform. For this you will need a client certificate and key and you might
   need a whitelisted IP or VPN connection. If you do not have this access, please contact the ops team.
2. Configure  `app.healthcare_provider=zorgab` in order to use the ZorgAB healthcare provider.
3. Configure the following settings in the config:

    ```
    [zorgab]
    mtls_cert_file=secrets/mgo.cert
    mtls_key_file=secrets/mgo.key
    mtls_chain_file=secrets/chain.cert
    ```

    In this configuration, the mgo.cert is the certificate file (in PEM format) for the client, mgo.key is the private key file (in PEM format) for the client. `mtls_chain_file` is the
    certificate chain for the mgo.cert. This depends on who issued the certificate, but it will probably look like this:


    ```
    https://certificaat.kpn.com/installatie-en-gebruik/installatie/ca-certificaten/kpn-private-ca-g1/

    Staat der Nederlanden Private Root CA G1
    ↪ Staat der Nederlanden Private Services CA – G1
        ↪ KPN BV PKIoverheid Private Services CA – G1
   ```

    Be aware that you must copy all the cert files into a single chain.cert file AND that the files are in PEM format.

4. When searching for healthcare providers in the LOAD API, it should now return the healthcare providers from the ZorgAB platform.
