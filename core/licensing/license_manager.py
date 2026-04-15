# core/licensing/license_manager.py
# Основной менеджер лицензий

import os
import json
import base64
import hashlib
import platform
import subprocess
import requests
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from .license_utils import CryptoUtils


class LicenseManager:
    """Управляет лицензиями приложения."""

    def __init__(self):
        self._key_seed = "y8wLv351s1NcIwYHLpROuxw9yMTpepbo7BntVtGzX5qGwvv8Gm"
        self._string_seed = "f1FC5JklRcSbveFQgVugCor9Tmy9X4tA6mbkEKBmFW6nU8P75C"
        self._command_seed = "TSfGjE4li7dAZIlyXo42F45Zhw5dubhTk3yguOFZt8SgC0WVnH"

        self._encrypted_server_public = "Z0FBQUFBQm9vaDRLMGdUWWU3YkNxUzlzbXRhTTBKX0UxZzR2YnB1TklDQlpJMnBRSW5xb3d4QzkybU1PTXFPODJmSGkwdGhhdUhtR3RzMDY5c1J0cXYzSGwwRExDVGR5MEppZ2RoQzJNVTlpQjJQMkxKLXhxTW5haG81MDVKdkVLdFhwWndzNTZIQlR5TFBVUGdlX01qcVZvOTctbFlsSm9CcTdRaHYtb1NOSGxpWkpIUnByWTRHTmtzeVdCcnpiNnF1WnhnMXFhQ1RhRW9TbnZMdnVnczdkUUlLaE1IUzVwU2hEWk9YZ0taN1A5NnY4ak5TYzZua0FpM3BSYmJLVnlTS1d1X1p4LUpSRUVpSTBFNTR5N3dPSjMxS3JWbVNVZ19WeWpiZEFWcTJQTkYyUEZwOFBPLUlQY0VCZThNUHVSRHh2cHlhMUx0aXZSb3FmdVhyUnlJWGVLWGZqNHFoR1ZhaE1ZcjFmdTd5azBlbGpJQkJ6QW9qY3lXX0x2T2NxOTVlZmJZTTlQSWhOU1BSVDRkUXQ2ZzVndmpCcTA0aFBnbVB3bWdGV1V5VXB6d05IMnRXX1g1Y3BlZHQxdkl0LWZTNS1KdUpYb1pFNGwtN1NEUGtyZDZuQ2g4Z2JGT2lOcnRqU2l3YzlEVUVHUnRLX3EtNmVCWTA5MUhyTURxSTNIXzkzN1AxVmRTYVJmWUVnck1Xc2JYRy02SS11OVZlSU5LQzdUeFNrdXEyTXREN1R4aThvQ2ktOHNqdV94TS1DVnRCcDNkcmQtNUg3cFlYa0lreXFfWjMwWXpVejlmYVRkbmtOZ3N6d1ZXbmtzUWMzQ3N1aThZR2h1UEhMWEdkTTVnMnRWLWNRc0Q0cXZJVXlXMUFOZ3E5bWZsWFhPaWpjMkl0Y3VZOTNTbk1FWnctajN5dVZGNHJWVTFrRHI2Wk9lZkFPeGx5aUpJOEZtTlFoNnpmdE9pZl9aelcwd2FRSkZaSHR0amdCNUl5MkRuRFJoSXlsNGlESFQwdmVEWlRRSjItYU9HbGZVQjhHZVlJdmtES05kOW1ya1RzdFdPalZGVTJJbXhNMlhrVlR2Skc5d0wxeGxsdzRHTi03bEgxUmhpSHIyRjhWZVVjV25IR1BwMTNYTm92UmJmNzV1Wno1R2g1MzRRV2pBUC01UllwY3Z0bENZbkJ1YlZESml3RjA0dm5wNU1WYnlwY0hfVUlsQV9DZkRoWWdrZGtGWDVObENGV0kxRjZ4Wlk2ci1ZWjhXQlVIZW10NFpDMVZSNlVCejVqM1Z4amIyZnloUkNJNWJwZFBiV1pLRVlZWjV1U3ZweTFhVUFwV3B5Z2FITmh6MUo2WDJaeU5vVWhpRXBFNTZxTDJMZXl3Zl8xcFdmLU9DSUZRNlRIMTJIZWRNbGI1eFhxMWUwQUtDMG1fdksyWUk5VUw0aDVtQnc1NGlSeFNZS3Npa1FpckVqdHRzQzNzZFNOcFNjSFpKZ2JMdFR1cGFUTXhxcWROdTV3YnNQUXpVODBFNnE2Vmtwd3pmVWRHeGp3cFZMZENoVkxw"
        self._encrypted_content_public = "Z0FBQUFBQm9vaDRLUV9nOURBTjRZT2lNR0hZVmhacm16RXJiU1JMUi1sOWNSYXBHVWZ1RjRIdVVBUHhxVF9ZR3paZVhZNWhfRFJKU0d4YVJJS2RRSWc3aFpmWjdmOF9RaUFtWmh1b0tOc2FiU1RyN3JYamRHVzNtcFpmcjJoRS0tZEstQ1k2cnJDTDRVX1BXbGU5RFNwM25FeGhOWjJBNFVBNXZtc3RWY19lTzVVYm5vQnFleEF0dlA3NGp5S2RTYWRZQmVoRkoxN2NzMDVGRWczZzE1U2Z0bVNhNnNNRHNaWjQ4THBjdXRCdGpuODZVbklFMzVXNjRfcGZMVTB4Q1R4LVRpSnJkM1ZDZWNOazJCMVBJUmtIcnUxRHk0SFZUYmFVaHlXaHMwX2xGT1NEZktJOU5QNXBnUUJwU0w3QktKMjJaUUJqUnRhSFo5NV9FcGNLWU95NVdBMlR0RkVlaHlpTW9sZVZ2Z0pOMC1ST25iWVRVNDdpZVZZdGRiVWpucW02dERFYUJjbEpWa0tMVGVXcnBaelRRZm1nMkc3SS12bWJQTDlNOWoycUZnU2NLdjdGQnQ2bG13YV92M2V2SFZYWTVxcFE4UjNuM2trbUZGM25SWTJUMkxuUzFFd1FyT1l3dW1EU0JIaDVOdmcwaXZjOUxqMXEwNFZOLXJ6Unc3eU5nMnNXZk9EV0FmbGZ0eE1PdlBvdTBBaTJPbnItaTVzSUFPVnZ0REE2eDZpX0lFcnRrcUh1Y19zVzVpbUhJSnhnaW9RLXAwRzRiWXM2X1hMOFhCY3pycTVLSDhfZEN3NUFxSE8xeWVucHpMX1M4MXhnUGttaFRVbWZRdVFLdFJCUWI0NElyY21WQlhxUDd6eW5vSk12N0J5b0kzcmVLczFFcjZQOFBmdTBjR0hPd0djMXpIbHFmb3Y2V3QxZ0gxOFllRUprN1hpbjRfemlCX0liT0dPb08tdEk1VTNORUEzZWxrMDlrQUk0aUhpTG1SQ2ZERGRyWWlUR05DSkc3X2hjY2FjeGc2VzlWa1Z3dWQzeHBEbmduOTVXUHo3RFRQQ0VIZG05ZVlzekt1ZVE0QVR3T0EwMWlPSmZyMkczd05yMXJmNjd1MXk5OWdjS2R4NTdYYk9BQ003bEgyeERMLW5Rc2ZPMFdHNVgxYkYwSVV0cnpVTUpSd0J2eFIxVlJ4UDJxcWlIZk5wUnhSdjJKUWh5UDVNOWdVUHdvOUxqVE9yYlN6VVRQV3ExVkhCRmp6QzVSRW1KeklTZjFjQlpBS081VTFWcUhwNExBQjROREYtck9IdlQxeHh5U0hlRHA3TC14ZVNtYTZqMW5kV1dxWkNDZm1QaU1TbkJKWDBiNjVRc0NKS192RDRhdW14azZNelpZVWdQSERlMWNmc3NTSmZxV0xNeHBsdmZFSTFJZklWc2JTUFpCdXowRjdIb29TWUZuWmJDb3BpT3dLRkpTWjc2TEpBV09PVF9KNkFMVHJlZUVmRW5wTVJpbjAyb2ZsQ2VLMm56R3lTSndiek1LcThjYy1MdUI4VGdO"
        self._encrypted_content_private = "Z0FBQUFBQm9vaDRLR0ViQ1VobmRjaUVXRXFja085aTJ0ZHBkZmkzWjlaU0x3aWFhekpjaG5BTDI3Q2ZzUFFmSlFOeTJxQlJTT1Rkc3BTQ1lSY3FUQkVtNXN6cktkbDUybjdhcVdIOFl3d0oyZEcwMVhMM0JCRzdrRDVsTnBQYzNaYXljNXBfRnE0SzJCNDNwN1BJRDlBUktfTUpiZ2daMm52d09ndFUzaFhab2Q0djV1cTg1VUZvU3ZFVUkxV2l6TFpGY0J2UlViSENqaC1ZZDc5SDVJWlpsZUdabFVIZnhFMnVCdGhhVHFuVDQxcUFyRTFXbnNHaU9lbmFkTU1ZS1JhU1pKa0dFTTlBbGgtNEJfOG1DclBhLXdJZVFIMG9IQjVldW96U05YZk1xcC1xaDduVzlJTE42ci0wYktKYUxTbFRyQ1RsRnRuR3JUYWE2TVdTUkhxMUtEVDR5WTRUcExmRXJBOUc3N0ZaUnhKUk5LRS1YOVhDYjdqTzVmN1BqZUdQM0d0cHBfN3Z6M1J5X3ZHdGtTenZhRHZNQUFNZDdFUUdiVnZBcWRlTzliOV9OazZnaDlGZmRxR1RhRDBIVVMwVG1QZTFYUDZCanJxNWFSQmRoS2JhYVh2eEczaGV5TmpJYm9TZEpRYWhndUdTUWMwX0o2RGJudmR2Z3huQi1Ndkc3QmRCQ3E3R0tFbWtEeUR6emxES2lRWVR5V2RGak1xQTlXbnA2OXVkYVlfYkJoWVBmSE0zMUZNUm9PbWJMWUxGRGxBbFRHRXZsMzVCQV9iSVlsTnF0eXhwQ0x6d1Nfd21kenBkZVQ1NHN3TGFEY3dZYTZjSmx6SXZKVUpBZzVZcEczMkIyX0VpeUVDRExaX2tvQjdfRmsyZEFXSmxCWnpIaS14THVWVDN0ZzM2bmZfRzJhTnNnd1phQVVMeGZUZklyamtFNnJtUGZmN2lMSlZKNVgyMUkwakl6Yl8ydWxiSnJFbzhtWVpFZDBPakg1cVVyR2lUUkJZajdQU3g2bU4wYi00M0VoOHltdDRhV3MwN1VkY1JwY1NFYjdYSHlTbUhmQzJBc0g2NWZoVWNuUGNlUXdza1BaQXRvbkV2d2VQbVBmWEdiVFhiRUZZckZFWDZidjBsSy1YU0JWNUxDdTNFd3FLZjFLVWdPZ2FsU3NTUXI2QWEtQWpxMXNQcVM0eDJOOEJ3M25MaklCVzFUR044Y3UyTmt2X3ltUE13VjV3dmtaanF6c0kwX21pX3AydTk4RnpRM3R0dnNMNUJoalotUGg4UkFna0xKMVhuSWZ6SXVrVzR4TUU4djlEcWdlczBPNTdic1lTUlZtNk96NDQzNXBnWHhkNjk4REgwWE9XVVNmSHVhQ0tYYlhDcXR3Q3hJRV90NE11U2I4VmVKR2hnZjVyeEhhdnZ2YWoxMkZ3b2NiWkF4OXdLOXNRZ1F2NWVkSnhZdEJhRnNnZEItclVxLUZCYU1HRUh5V1lKbzd2NkZEaE5JTGNEMlJ4TDFxdTJpdE9ZUnYwbDJyVHJEUDlLN1c4VG03ZXR2X1ljMVdrelRuQ09RNkVDTERTYzFJV0J4N2czaFFqYUxSZ0JrOEgyeFIxOTJQUDZjdVJMSktFN2s3VzdzSnlwektBZ0dkUlRKZVVNXzJQVE5GSzlTMEZMYl95cWpNSGJmYThxem4wMngtSkxuUkdOTDl4X0E0dFQ1a21PQlZnR181LXQwMnJqcUN4SWdtNEFYVWx0ZXQxVWNweFN1VjJnQzFxaG1GdEdlUFFZN0hQZkhlUDhmWjkxSXJOYUQzSWhfQW53RkxvTmxhWW9qN0ZzaDNZWkdRVm1IMnlqVFBRREZNSWd0V21Ydkd5WGNoYkJoZmFoV0Y2dGhHMnlha09FMnlLbDQ0am1hbzdvbmNxbFFIaGtrc3RfYlR2Y1h1cTlwSVN6aUNZNS1yQ0h1SFBZNE9OUHVsRXlYZndRaURwVHdoQm9VVEp2VGVraUQxZENza0Y4TkF6TlNyemJScXJqcVRfUjRxWEE1SnNpMmIzNUE1QlhMOUJ2ellMWTd4S2FLMXdibjFDbFNWSHp5dzBHOHFXMDM3VWRmVDZQRmZfZHZEREI2U0tRbGY1M3pxZW5LTG10eWVIczV1c2h4UWJfQ0QwdHJsS2pMaEtVQkVwNGR3dkVZT1NGaERDOWt5M2dWd3RQaGFnWXlNWXhsYUVzZE9BUllhejc2N0NadWNCaTRQMVpzZEx1TXE4c1BJczVUS2VnTFdOcERMMU9rckZrdXg1Zzd0bEVSYXVWVE5LeWpZd043bDdqaWlnNWZxSHJ6R1EyazFBYl9UTnQ2cWdxV2F2NnhPQUtGcnh2eFVUQU5lYjAtRnY2ekxnZVZ3c2hnOU1PVElPRHl0ZFY2OXRNY2pxaktzNE93ajFLVTZKdXZLRVFFMDF6Nm5jYlJkWllOWFYxR1F2NjJnVzJwbmNaWldqb0RCWGcyVDRqLUJmOTktTGlpQVpvOHIyU0VUMWVfNGhQLXhfaENSdjIxRzFVeUg5WVJFVHNfX1VlMlRqeHI0REoxRFlSak01b2V2NkhVVjhrRGpQNmtvSUpEdDR1aFhwR1ZsLUlJZWwxYmo1SFliUERhM09aRFF6VE0yTUNncWZqQnpGdlF4dDN6dzRlMUQ4MmlyWVFIbGhsXzAwTERDTGRYcnVMLWdMYmFqTVRDNm00MGgwVzlDUFNEQ3phaWcweS1XdUJBZktwSmtSVkNsb3NiQVIzSlY3QjAyMFBXOXR5Smk4YllHYk9yejlCRVJicTZJSFpBSUxYTURrQUw5NUdTaENJTGNpeU4tWTQyd2RWdWlLRzlLU0Z1RmRTX1F2b1ZIbTRHV0gxOTh4aHp1eUY5OGxxQ0txTGo2VGJEM3NhT2ZpeTY2Vmo4N3BJT3dhdjRsd1pIdlYwNzlxR3lvaVdKMFFJRVRMbFE3RFlkVXR2b3dWbF93OW9Wd1VCTlY2Sl9CWjNaZVc1ZHlSS0RmT2FUX3Jma0FLZVJpNzNodEFBbkczZFY4b25TTEhJQWZ4U1ZXbFJtZDVqU1NOMWZ6V1N6aGN2TWRvVW44d1pBVGJMb1lFMmF0TlFnV0JrUmt4cFMtU2lZUW56XzVQZllUU0dNTkRoczFUNTlEVGZFWkpJODk3aHdqUU52X3VreFhnRGZ0S0tESmc0SDRjaUl6ZDFpUzl2bG9qTFpwUWpCcDZfcXFEY1JvUjVmSUpKaC02TXVUUnNFOXVhd3FjX21MWFZZbFNlZEl0V2FDQ01obVd5YVpzd3QzX29fVjdxRmFLYlplcWlGVXJ1eUxtaGczRTYwOFY2aXRtbGlGZ0N6bnBHQzJUMnNiSEFsTnZDOGs5clJ2NGE0WkhSZmVLY29wU3pLeVJDaHBOSkZ4V2otODgtdjQtZWxTTWx0WHFwUHdzaFV1bDJfTFdubC16VUtucGtkNnNqVVhLTWF4cWxSZ3JubHJQN1J0Zkk4WnNRMHliVDhhOGQ4T1BSam5MVUdrQ0NMZEFiSmRjR1J0Tmo4cnAyWF9vcTBRdURqbmFXdUFRYmVJUHJGQkVFRUg3a1hvdHloWnYxVmVlTUx6MUpVSi1FV0pZYThzb25yTFZDNnJsejNJa25ONThCbXZ3akN6SGJYZi0zNzBObE9xbTZaakEtalpWaDJBZlA0SzByQ0xmc2tBSkFDSUlCY1NmRnZvYWFPcF83ZUR4VDZiOFlUWi00RWo3Q0tOSXBDWTBRbkZnVjA0ZHZ1SmtKdVdmNmE0a1ViSEJFeGQ4bE4yLTZHaHNaMV91VW1ULWJkZXlxdlFkLWhORGlxaWFBdzRTVWJzb2xRSGVDb1k4UHpmV2dTb3BXS2l2TzlsSEpDa0I0M1pseVh2R3NEY2VJR2pnalVDRmh1R1o1U0tvc1A4TzVmNlBjZ3RmMzR3dkNNWnFTOFJzU1JhVTEtdVhZMHhOdERBaXNJTXdyUVAwUTh5LXZHT2lfUkhJMkJXVTZERnN0LVZ4Slk3cWZhYzV4UGJocVlJanNRQ0xpSTh1UjFkTi1BcUxwWXV0YTVscjFlMElrZzJhNVI1TWF5empjaTcwTmxYZEk3RDFHTzdEazB2NHd4RDZCQWI1UG00ekVRc0M1Qll0ZTJtQ2xrc2pzazlZNW91ejlQVWI0d0U5TmJ4dzdmUS1JZkdhdGZ3SlNYTE9aejVGTzg3azZPTzMxQlRvbW85Y2ozVHVsZkJLZWhIRXJzUzR3SzQ5eWJjTC10eklCTlB1clBwWWVMWmJGd1hHQkxlUjFqYzNIdkNJMTNZbF9RTm9HLWtDRXh2N2hmOWRqdzFNS1J6QkRLeE5CS0JmTlZuOEN1MXlsS3JaM25tRzI1TEE1V3VHbzFmSnFCTVN6bWFqTnZkU1JBeGcwUkI5dFdtNlNlZmljdy1LZjUzQ2hCd2R0UGNCQ3V0VGw3RlVKWW1oNHFUTnRNZ2swLVpiZkx5ZUp3TmxXMXZpNFFtVC15UmdYVWRGN1B0czBSSmJXMlA3WjJpVUEtMGlwRVVkRmhuM0NKNkNtNjVpTEFhWHFLc2F1ZDU4TFZGSnRVWjBYRW1xZ2VDT0pnQ1o3bzZJZ2ZZS1NKYzluYTRFc2xRU2lwbkMzY3FXTWlOUVpsSXZ2ZTZlZS1XODFwb1RNY3BFb0VUbmNtekExQ09zTXVtcEJmNXJOZXJVVkxOOUk3Vl9ONkI1OGRzX29vWENjdk45Sm04QWhMT0JaNnR6eWRBaHJfVy1vMGVISm9ZVnIxS3Y1Y0VqUWtOclBjQUl3ZUdqaUNXOXhwLVR0dWJnU0x3TF9tWld0ZVNxTlkxT2h0RS1xaTl6bXFKa1JYN3g0MWc3V2I2bDhscmowXzl0NHlZQk1YbTc4VUcwVGpmVEY2VTNTN3FXZzRCdUlJT0tjQWt6MW1KT0oyU05vTXREZ0ZfLXNvelFqbUM4OXRZUTVBSWsySjhMdDljaV9jZ2I3WWNhTHFqcTRIM3VodFdCcjNTN1E5NHFJR0JWNFVHZGl2ZE1LWXRPdldnSU1vQURLWl9YNDF5U1A2LXREbnNfenBpb2VyWU14d0RDeW5JMGhwWWxGZ3NQMkxuWEVIX1dSdDA0TEdXZG5EVW90S0duc21aRWp4NDNRQW40RGpSTWFjOVlvTURZZlllWGc4VUVHSlFHUF9ObUtvamNjbUh4ZnF3SFR2NmZFSGVYRUt2WVdTRzFyZ1BNdWZCcEZSMEZKZ2Vnc2RSWHlnNW9ITWRXTjREd1hUT1FxS3V1V3N6ck1YYkpLNDFiQ1Y0VDh5cFdpR3NtbVFrVzY4eHN5TDN2c2lzb0tzbTNYQzZ0TWRxWU1HSWF0eFUtZTJIdUV1MW1lV3YzcEdQTTdDNGhXTmJUZ19hZXlPMUxJN241UlNMWnpkdHFRN0s0TkdkeV9OTUZXMWJQS3dHcFA5UFBMaUFGMHNxOW5Ga19yYmNYRXR6ZzQzMkxIRVBpaHo2Tl9IOUduRGZKbDIySHplSEhUOVJVZ3lHbkY3TWxSMkNiSlp6RzBhY1ZFYmJidTBVS2NqbDQ0OG16TDRjakp0djAwcnN0SF9nSnhnNXYxT0pMX0EtSThHUDZKbTJFNmRSZ1R6OVBFRFFsX3ZDeGJzODZWcW1WUm9EUk1CaXVQcVFwWTJQQUh2dmdRWHc4ZVZGVThYRFRTZnZzRkhkRnJqQXVQcC0teVk3Y0ZkV0puUHVWRWxkWVhBZ2hlbElmX19md3VqMVA4Y0sxY1g2U2paZlAwejVBZVBVS3U2WENKWlZ5clU2U2VDdS1yaEVfU1V0cF8zZi1LbE5nMGRoYkJ3MDdlM0Z4TWV3bG5lbE5KVVQ3cnotOUJZRWdwTWFUQ1lHTFFFYmJrRjNET1VTUkFZSmtwd0FKQkZDLVhra2Y5NXBMMnVEbnVJc1Q0YUFCQVROQT09"

 #       self._enc_str_0 = "Z0FBQUFBQm9ycjMzcGFBVUFLTkRpWUIxR1d5UVFKZ2prTEh0SmFsX1hiVDZDN1lPNVFVSGwwc2U1ZVVhNkQ0MktZNFBuaWNybHJjaEEwLUlGaTRadHhTNFg3Sk1LMWhia01Bd2RDWHNEMUloT2hheHgyWXB4NDBpLUtYbXNtTmk3QmVyM0x6TVNhdk0="
        self._enc_str_0 = "gAAAAABpjjaSaZdiNiyMEo9Ohvc2f4uYQfex98w3cnF1L6L6CcYejC27p6NwG-WPqEwgPq7Rp6LN9O5ZMXmCYPb7TkvaIpi6CZOBmMvf-GGswGaZ68N4vL0="
        self._enc_str_1 = "gAAAAABpjjaSkyRxUA7Reh1eKw6ckcTY4yrcvRybJgVLshITXBFoE0Ri_Xeb0rEYnV2Vuq4RhZojUhkK5Hk1Z_cVN_IXpCIb6ZHT0veJc1UTAQCWr4qr5KM="
        #self._enc_str_1 = "Z0FBQUFBQm9ycjMzT0ZmV1M2WklEWWs4ZFM4TGROekd2VDVoaFBlN2lLaW1RcWlldVpSNGZDLXRJTWNsTnNnSE1ST3dUQk5pWUg0NGtlYTkyREpaSktxVzV5elcyY0lSLVozbHN5UGdPYWM4LXozRGJkclJ3emVKMUJCZEVPNWxLSTlSTW5EelVtaVpib2wzb1RjcGp4eW9pNWozQjZaTkV3ZkV0ek1YMURIVjdJR3hJSTYwbjJaVGRMc0g5UG5FVWhSZjU4V2hlMEJJQnd2RnVETUVuV2NYWFZWTnBrZFpYY0EwQW9LWUQ0cHZicnQyajZtSW93M3pKZE1sbXBfMVhuWnVJTHpQYXMyYVd1enJWZGlpU1hTLVJKNHMxZnNGQ3c9PQ=="
        self._enc_str_2 = "Z0FBQUFBQm9ycjMzcDZiVUgwYmstdDhNVWR4YmY0UEpzZ2doNFFCdS0yUk5PNXl2U3c0MW1MejFxek1kN2VZX21mLVNuN2NEOFFZWi1GdjB4SEhCMi1rMHVZUkI2Ukp6TVE9PQ=="
        self._enc_str_3 = "Z0FBQUFBQm9ycjMzVEhjZWp6V1BHMzZQcHg3c2Nuem5xelFzam5rSnVqckFzMzlIYTVPVTRXY1RLRnNzUmhiYmpvU29ZNDFLMG9na2RtY1o2Tmx2dmFaNVo1a0p1Z2hRVHc9PQ=="
        self._enc_str_4 = "Z0FBQUFBQm9ycjM0UlUtZ05VcjZuSE9TbEZYNUVyWFJXUWlwNzA4Q2wwc21mU3Y5dVJnMjB1Tm9VZkxnYi14dGJhRWlhZU9pUzd6ckJjNDJFdFZqb3A0Sl9lY0doZUFPUEE9PQ=="
        self._enc_str_5 = "Z0FBQUFBQm9ycjM0TkVkM1E1MzIwQnlYRWROWGp1LTJmM1JOTDRKbEMyVFRzVUpWS1dqYmV3UzNqblVVVDhhNVdRSkx4R216OGJuNGx0OWl5UFJ1bVhLbzMwMzhZTWxBbUkzaXplcnE2T0RlQmFZTVR1LTRYdUk9"
        self._enc_str_6 = "Z0FBQUFBQm9ycjM0YzAtNXRJSVlSTWdaZ1pfTzBrVUJZM1VVcFpjbXdvdFQ4QkptZTNleDFOUFBxMllGU05xNnh2RWpycnktVVU2a3kwNXI1NmViQkN0YThuT2Jyd19rX2c9PQ=="
        self._enc_str_7 = "gAAAAABpjjaSyV-YppmWOdu99USaqndMxlpitIe8iVDgM34VK9FhEH-K6zAzVY_0QLSx7-3qTzpw-mgt0Tjw_6xLwdQwbjUJsJ0fIJlgSpMDbV5GCjJ82hA="
        #self._enc_str_7 = "Z0FBQUFBQm9ycjM0N1Y1SEZmSEV1X1hDc2tVeWVmTXpFcWQ3VUdUSktEamwwc1BKWXUybVZOamFmenNyZVB3VW1hRGtrTnFReHdvRFBEOEdJdkhXd2JvSmJqSVFMMFZJT1E9PQ=="
        self._enc_str_8 = "Z0FBQUFBQm9ycjM0YjJXMnJhcFNHVXBMX2FnVGE1Q1l0WktOUXBOWFhzSmZNM3dQQm9JMjduanUtWnZtNDlOUHJwWUpWZ0VPaDlvd2FjSHcyNE1jYV9lamQxVWItOUpNQ0E9PQ=="
        self._enc_str_9 = "Z0FBQUFBQm9ycjM0VGp6bjR0bVdpbXpVR3BERWxHNHBFNlhWWXNCbW04akJvZjRSRjZPOHZwZkdfeEZVek9menVFc0treWNFd25jb21STXZzNDN4NTdsLWVadkdkRG5tdnc9PQ=="
        self._enc_str_10 = "Z0FBQUFBQm9ycjM0MUtGc0pkNDJNTUIxZ1FtdXk3TktSa1RQMHR4TVBrZlhkMWFfUk9lUTdNUmNJdExGOUdVMjRCbzhqb1RodGpmSGlRMHdiYUdMbklZbzhWdkkzeWp4Nnc9PQ=="
        self._enc_str_11 = "gAAAAABpjjdZOQaOIsWfNEp9rFH55RDIPpOvor6rcW3WMutdRxjf40SvBCPhryHkTpNdFXpHtu7C_5VqzLthxo4ztsNhAv7ePQ=="
        self._enc_str_12 = "Z0FBQUFBQm9ycjM0T2ljX016ZnM0Nlc3VDBaZTVpRWRxMzQzelVycFk3TXRGTWF6cVNoMmQtMktvZDYwdGRDSnNDZEZITDZBWGM2cmFRVUlnbUtBamE1Z0xxM0dsS3dKWUE9PQ=="
        self._enc_str_13 = "Z0FBQUFBQm9ycjM0Z2U0T2EtNGRXTlEzb0ZSNExjbTQtWS1XZTRPY0ZJZ0xNZE1PM0tiMkIxU3psbnBtM1hnNFFwWXhwOGRxdUlfVVNGNDF3aGtMSHVjY28xYU5CSFUxemc9PQ=="
        self._enc_str_14 = "Z0FBQUFBQm9ycjM0WlJfYWVLaWVKOHpveWNrbEVkNVg3LWdOV1drdUJsLWFLb1pEYUJWN2tyN1ZBczBSSm9RdF9WX2EwcG9kWG9ZQVN0OXV2OXBDZnJZbjhpeFR3WVVodVE9PQ=="
        self._enc_str_15 = "Z0FBQUFBQm9ycjM0VS1keUo2Y21xaEFhQzd5VndhT2taTFNUdFBqTFY3N01qYTNPeVpPaVNjcjJUWXZkb0xxb1dBVHY0THRyMTVKNlFIQzVwWEg5RE84YUl0b1FKcVlmYXc9PQ=="
        self._enc_str_16 = "Z0FBQUFBQm9ycjM0NjhIbkczX0dDaUlSZWV2XzdBWjhZTWRQMjZWOFhPTXJkSkJ4dXREcFA1ODFMWGUtSjBEcjdCMWNSS21Gd3UtZGpaci1Jc1lfbnBtOXRhY0p6OGJ4VUE9PQ=="

        self._enc_cmd_0 = "Z0FBQUFBQm9ycjM0OUpXUC1BMzFlOUxRTW55QXRHOXN2SExIeDZNRUN6cHZ6cWdqU3ZQQklocmlYOHhyZzBfSUQwbi1uYm1xSXZyakh0UFAzZWUxRXVvRTV0amxWNFZMTWc9PQ=="
        self._enc_cmd_1 = "Z0FBQUFBQm9ycjM0Nk1laFRRbFpSY3JWeW04SG5ycmtNa1RHcVk5bGdjQ2Nid3BBMmdJdFZUUFU4bTEwWmU3bXFVRjA3S2hSOWtPb2NKRnhLRlo5VG9jLUc1Y1ZHS1diblE9PQ=="
        self._enc_cmd_2 = "Z0FBQUFBQm9ycjM0Q2NSc1VEQUNDNTVRN0RqMy05Y1dDSElPYnBkU0YwTnkySGlmeEVQbXcyRk55VHhQWU0xblpReHBmTjRGVWdVSDM1WE1ERG50LVBRczFDdmg0Z2luMEE9PQ=="
        self._enc_cmd_3 = "Z0FBQUFBQm9ycjM0MWFzMzdnaHRmS1ZtZ3BsT2ZkN1d0RDM1OTVydTNMVDZFUHh2aEtGcFRPRlAwQ1doQWJfdmRHa1h2eVVoMGt1ZzIteFNmRHNfcjkzTWhmU2FnT1R5SGc9PQ=="
        self._enc_cmd_4 = "Z0FBQUFBQm9ycjM0UzRMakUxZFF6aGppcHhJamxqWWo3Nnh0YTFTUFp3cU50Wmd4MzlLVnRzMFpHT2I3Z0FtaFFjeVltMFpRSTBCVUxuYUdFZ0hERkQwbDZKSzAyb3lhamc9PQ=="
        self._enc_cmd_5 = "Z0FBQUFBQm9ycjM0TVpvX0JIZWdZbEJJY19DbGFycXZaU2xzRWdsTXJMTnVHSHVzMzNUWnJINFI4XzRQVy1SdDNCUlRXMzdSYWZPbVZiN3hsTEd2SUllVElVUVZsdGp4QlE9PQ=="
        self._enc_cmd_6 = "Z0FBQUFBQm9ycjM0MVVZSndBaEl1OXQzYk10Tm1JUGl0Q1lBcldyYkhiS05lS3BGaGtaQnE3RTlRMEd4azdMOHB5akRnWkR6NjdVMTcyMDk2VGtDZzh6eXkxRVZsclNrOHc9PQ=="
        self._enc_cmd_7 = "Z0FBQUFBQm9ycjM0S3dnSU9nenJ1VnpzOFpiTmR6YUdCNDZWRS0yejZEcHVNTWpxYThmT21QWUNHTUJCMElub3N1QzlvWHFDbDh6QlBQSVktWXJGV2gtSklkNlNpMFJRaFE9PQ=="
        self._enc_cmd_8 = "Z0FBQUFBQm9ycjM0ZVlLc2FSRWNlNmN2cGItbmVGdjBxTXNadmN6SC1rdE1hSkJ3X25fYS1OSm02SVJkcGg0YTZKN0tDLXJEeXZaRUpsV2RHYTNDNFB6aXhOOUVPaXZJclE9PQ=="

        lumo_folder = CryptoUtils.decrypt_string(self._enc_str_2, self._string_seed)
        license_file = CryptoUtils.decrypt_string(self._enc_str_3, self._string_seed)
        self.license_file_path = os.path.join(os.path.expanduser("~"), lumo_folder, license_file)

    def _get_decrypted_string(self, encrypted_var: str) -> str:
        """Дешифрует зашифрованную строку."""
        return CryptoUtils.decrypt_string(encrypted_var, self._string_seed)

    def _get_decrypted_command(self, encrypted_var: str) -> str:
        """Дешифрует зашифрованную команду."""
        return CryptoUtils.decrypt_string(encrypted_var, self._command_seed)

    # ... (остальные методы без изменений) ...
    def _get_server_public_key(self) -> rsa.RSAPublicKey:
        """Возвращает серверный публичный RSA ключ."""
        try:
            decrypted_pem = CryptoUtils.decrypt_string(self._encrypted_server_public, self._key_seed)
            return serialization.load_pem_public_key(decrypted_pem.encode())
        except Exception as e:
            print(f"Ошибка загрузки серверного публичного ключа: {e}")
            return None

    def _get_content_public_key(self) -> rsa.RSAPublicKey:
        """Возвращает контентный публичный RSA ключ."""
        try:
            decrypted_pem = CryptoUtils.decrypt_string(self._encrypted_content_public, self._key_seed)
            return serialization.load_pem_public_key(decrypted_pem.encode())
        except Exception as e:
            print(f"Ошибка загрузки контентного публичного ключа: {e}")
            return None

    def _get_content_private_key(self) -> rsa.RSAPrivateKey:
        """Возвращает контентный приватный RSA ключ."""
        try:
            decrypted_pem = CryptoUtils.decrypt_string(self._encrypted_content_private, self._key_seed)
            return serialization.load_pem_private_key(decrypted_pem.encode(), password=None)
        except Exception as e:
            print(f"Ошибка загрузки контентного приватного ключа: {e}")
            return None

    def _run_wmic_command(self, args: list) -> Optional[str]:
        """Выполняет команду WMIC и возвращает очищенный результат."""
        try:
            cmd_wmic = self._get_decrypted_command(self._enc_cmd_0)  # 'wmic'
            cmd_get = self._get_decrypted_command(self._enc_cmd_2)  # 'get'

            full_command = [cmd_wmic] + args

            # Создаем стартовую информацию для скрытия окна консоли
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )

            # Очистка вывода: берем последнюю непустую строку
            lines = result.stdout.strip().split('\n')
            last_line = next((line.strip() for line in reversed(lines) if line.strip()), None)

            # Проверяем, что результат не является просто названием поля
            if last_line and last_line.lower() != args[-1].lower():
                return last_line
            return None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None


    def _get_hardware_id(self) -> str:
        """Bazadagi formatga (44 belgili Base64 SHA256) 100% mos keluvchi HWID."""
        system_info = []

        if platform.system() == "Windows":
            # 1. UUID
            cmd_csproduct = self._get_decrypted_command(self._enc_cmd_6)
            cmd_uuid = self._get_decrypted_command(self._enc_cmd_7)
            system_uuid = self._run_wmic_command([cmd_csproduct, 'get', cmd_uuid])
            if system_uuid: system_info.append(system_uuid)

            # 2. CPU ID
            cmd_cpu = self._get_decrypted_command(self._enc_cmd_1)
            cmd_processor_id = self._get_decrypted_command(self._enc_cmd_3)
            cpu_id = self._run_wmic_command([cmd_cpu, 'get', cmd_processor_id])
            if cpu_id: system_info.append(cpu_id)

        # Ma'lumotlarni birlashtirish
        combined = '|'.join(sorted(filter(None, system_info))) if system_info else platform.node()
        
        # SHA256 xeshini byte ko'rinishida olamiz
        hash_bytes = hashlib.sha256(combined.encode()).digest()
        # Uni Base64 ga o'tkazamiz (aynan bazadagi kabi 44 belgi chiqadi)
        hwid_base64 = base64.b64encode(hash_bytes).decode('utf-8')

        # DEBUG uchun terminalda ko'ramiz
        print(f"\n[DEBUG] Local HWID: {hwid_base64}")
        return hwid_base64

    def _encrypt_for_server(self, data: str) -> str:
        """Шифрует данные публичным ключом сервера."""
        try:
            public_key = self._get_server_public_key()
            if not public_key:
                return ""

            encrypted = public_key.encrypt(
                data.encode('utf-8'),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            print(f"Ошибка шифрования для сервера: {e}")
            return ""

    def _encrypt_content(self, data: str) -> bytes:
        """Шифрует контент публичным ключом для хранения."""
        try:
            public_key = self._get_content_public_key()
            if not public_key:
                return b""

            encrypted = public_key.encrypt(
                data.encode('utf-8'),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return encrypted
        except Exception as e:
            print(f"Ошибка шифрования контента: {e}")
            return b""

    def _decrypt_content(self, encrypted_data: bytes) -> str:
        """Дешифрует контент приватным ключом."""
        try:
            private_key = self._get_content_private_key()
            if not private_key:
                return ""

            decrypted = private_key.decrypt(
                encrypted_data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return decrypted.decode('utf-8')
        except Exception as e:
            print(f"Ошибка дешифровки контента: {e}")
            return ""

    def get_encrypted_identifier(self) -> str:
        """Возвращает зашифрованный идентификатор пользователя."""
        hwid = self._get_hardware_id()
        return self._encrypt_for_server(hwid)

    def _save_license(self, license_data: Dict[str, Any]) -> bool:
        """Сохраняет лицензию в зашифрованном виде."""
        try:
            os.makedirs(os.path.dirname(self.license_file_path), exist_ok=True)

            # Шифруем данные лицензии
            json_data = json.dumps(license_data)
            encrypted_data = self._encrypt_content(json_data)

            with open(self.license_file_path, 'wb') as f:
                f.write(encrypted_data)

            return True
        except Exception as e:
            print(f"Ошибка сохранения лицензии: {e}")
            return False

    def _load_license(self) -> Optional[Dict[str, Any]]:
        """Загружает и дешифрует лицензию."""
        try:
            if not os.path.exists(self.license_file_path):
                return None

            with open(self.license_file_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_json = self._decrypt_content(encrypted_data)
            if not decrypted_json:
                return None

            return json.loads(decrypted_json)
        except Exception as e:
            print(f"Ошибка загрузки лицензии: {e}")
            return None

    def validate_license_online(self, license_key: str) -> tuple[bool, str]:
        """Лицензияни серверda автоматик текшириш."""
        try:
            # Yangilangan (44 belgili) HWIDni olamiz
            hwid = self._get_hardware_id()

            full_url = "https://lumoserver.ru/api/license_key/validate"
            client_api_key = "client-secret-key-12345"

            # Muhim: HWID endi bazaga mos formatda shifrlanadi
            payload = {
                "LicenseKey": license_key,
                "Hwid": self._encrypt_for_server(hwid), 
                "Action": "validate"
            }

            headers = {
                "Content-Type": "application/json",
                "X-Client-Key": client_api_key
            }

            response = requests.post(
                full_url, json=payload, headers=headers, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # Server 'valid' yoki 'status' qaytarishiga qarab tekshiramiz
                if data.get("valid") is True or data.get("status") == "active":
                    license_data = {
                        "key": license_key,
                        "hwid": hwid, # Toza xeshni saqlaymiz
                        "validated_at": data.get("timestamp", ""),
                        "status": "active"
                    }
                    self._save_license(license_data)
                    return True, "Лицензия подтверждена"
                else:
                    return False, data.get("message", "Лицензия не активна")
            else:
                return False, f"Server xatosi: {response.status_code}"

        except Exception as e:
            return False, f"Ulanishda xato: {str(e)}"
        
    def is_licensed(self) -> bool:
        """Проверяет, есть ли действующая лицензия."""
        license_data = self._load_license()
        if not license_data:
            return False

        # Проверяем HWID
        current_hwid = self._get_hardware_id()
        stored_hwid = license_data.get("hwid", "")

        if current_hwid != stored_hwid:
            return False

        # Проверяем статус
        status_field = self._get_decrypted_string(self._enc_str_15)
        active_status = self._get_decrypted_string(self._enc_str_16)
        if license_data.get(status_field) != active_status:
            return False

        if self.validate_license_online(license_data.get("key"))[0] == False:
            return False

        return True

    def get_license_info(self) -> Optional[Dict[str, Any]]:
        """Возвращает информацию о текущей лицензии."""
        return self._load_license()
