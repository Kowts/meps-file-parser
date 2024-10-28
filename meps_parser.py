from dataclasses import dataclass
from datetime import datetime
from typing import List, Union, Dict
from decimal import Decimal

@dataclass
class MEPSHeader:
    tipreg: str          # Type of record (0)
    fich: str           # File type ("MEPS")
    idinstori: str      # Origin institution ID
    idinstdes: str      # Destination institution ID
    idfich: str         # File ID
    idfichant: str      # Previous file ID
    entidade: str       # Entity
    codmoeda: str       # Currency code
    taxaiva: str        # VAT rate
    idfichedst: str     # EDST file ID

@dataclass
class MEPSDetail:
    tipreg: str          # Type of record (2)
    codproc: str        # Processing code
    idlog: str          # Log ID
    nrlog: str          # Central log number
    dthora: str         # Date/time
    montpgps: Decimal   # Payment amount
    tarifaps: Decimal   # Fee
    tipoterm: str       # Terminal type
    idterminal: str     # Terminal ID
    identranps: str     # Local transaction ID
    locmorter: str      # Terminal location
    refpag: str         # Payment reference
    modenv: str         # Communication mode
    codresp: str        # Response code
    nridresps: str      # Company message ID
    version: int        # Version of record (1 or 2)

@dataclass
class MEPSTrailer:
    tipreg: str          # Type of record (9)
    totreg: int         # Number of records
    montranps: Decimal  # Total transaction amount
    tottarps: Decimal   # Total fees
    valiva: Decimal     # VAT amount

class MEPSFileParser:
    def __init__(self):
        self.header: MEPSHeader = None
        self.details: List[MEPSDetail] = []
        self.trailer: MEPSTrailer = None

    def parse_header(self, line: str) -> MEPSHeader:
        """Parse header record (type 0)"""
        return MEPSHeader(
            tipreg=line[0:1],
            fich=line[1:5].strip(),
            idinstori=line[5:13].strip(),
            idinstdes=line[13:21].strip(),
            idfich=line[21:32].strip(),
            idfichant=line[32:43].strip(),
            entidade=line[46:51].strip(),
            codmoeda=line[51:54].strip(),
            taxaiva=line[54:57].strip(),
            idfichedst=line[57:68].strip()
        )

    def parse_detail(self, line: str) -> MEPSDetail:
        """Parse detail record (type 2) for both version 1 and 2"""
        # Determine version based on line length and structure
        version = 2 if len(line.strip()) >= 103 else 1

        if version == 1:
            return MEPSDetail(
                tipreg=line[0:1],
                codproc=line[1:3].strip(),
                idlog=line[3:7].strip(),
                nrlog=line[7:15].strip(),
                dthora=line[15:29].strip(),
                montpgps=Decimal(line[29:39].strip()) / 100,  # Convert to decimal
                tarifaps=Decimal(line[39:44].strip()) / 100,  # Convert to decimal
                tipoterm=line[44:45].strip(),
                idterminal=line[45:55].strip(),
                identranps=line[55:60].strip(),
                locmorter=line[60:75].strip(),
                refpag=line[75:84].strip(),
                modenv=line[84:85].strip(),
                codresp=line[85:86].strip(),
                nridresps=line[86:98].strip(),
                version=1
            )
        else:
            return MEPSDetail(
                tipreg=line[0:1],
                codproc=line[1:3].strip(),
                idlog=line[3:7].strip(),
                nrlog=line[7:15].strip(),
                dthora=line[15:29].strip(),
                montpgps=Decimal(line[29:39].strip()) / 100,  # Convert to decimal
                tarifaps=Decimal(line[39:49].strip()) / 100,  # Convert to decimal
                tipoterm=line[49:50].strip(),
                idterminal=line[50:60].strip(),
                identranps=line[60:65].strip(),
                locmorter=line[65:80].strip(),
                refpag=line[80:89].strip(),
                modenv=line[89:90].strip(),
                codresp=line[90:91].strip(),
                nridresps=line[91:103].strip(),
                version=2
            )

    def parse_trailer(self, line: str) -> MEPSTrailer:
        """Parse trailer record (type 9)"""
        return MEPSTrailer(
            tipreg=line[0:1],
            totreg=int(line[1:9].strip()),
            montranps=Decimal(line[9:25].strip()) / 100,  # Convert to decimal
            tottarps=Decimal(line[25:37].strip()) / 100,  # Convert to decimal
            valiva=Decimal(line[37:49].strip()) / 100     # Convert to decimal
        )

    def parse_file(self, file_path: str) -> Dict[str, Union[MEPSHeader, List[MEPSDetail], MEPSTrailer]]:
        """Parse complete MEPS file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if not line.strip():
                    continue

                record_type = line[0:1]

                if record_type == '0':
                    self.header = self.parse_header(line)
                elif record_type == '2':
                    self.details.append(self.parse_detail(line))
                elif record_type == '9':
                    self.trailer = self.parse_trailer(line)

        # Validate file structure
        self._validate_file()

        return {
            'header': self.header,
            'details': self.details,
            'trailer': self.trailer
        }

    def _validate_file(self):
        """Validate file structure and contents"""
        if not self.header:
            raise ValueError("Missing header record")
        if not self.trailer:
            raise ValueError("Missing trailer record")
        if not self.details:
            raise ValueError("No detail records found")

        # Validate record count
        if len(self.details) != self.trailer.totreg:
            raise ValueError(f"Record count mismatch. Expected {self.trailer.totreg}, got {len(self.details)}")

        # Validate total amounts
        total_montpgps = sum(detail.montpgps for detail in self.details)
        total_tarifaps = sum(detail.tarifaps for detail in self.details)

        expected_montranps = total_montpgps - total_tarifaps

        if abs(expected_montranps - self.trailer.montranps) > Decimal('0.01'):
            raise ValueError(f"Amount mismatch. Expected {expected_montranps}, got {self.trailer.montranps}")

        if abs(total_tarifaps - self.trailer.tottarps) > Decimal('0.01'):
            raise ValueError(f"Fee mismatch. Expected {total_tarifaps}, got {self.trailer.tottarps}")
