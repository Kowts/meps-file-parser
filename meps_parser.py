from dataclasses import dataclass, field
from datetime import datetime
import os
import re
from typing import List, Union, Dict, Optional, Iterator
from decimal import Decimal
import logging
from enum import Enum
from pathlib import Path
import csv
from io import StringIO
import json
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MEPSParser')

class MEPSError(Exception):
    """Base exception for MEPS parser errors"""
    pass

class MEPSValidationError(MEPSError):
    """Raised when file validation fails"""
    pass

class MEPSParsingError(MEPSError):
    """Raised when parsing fails"""
    pass

class TerminalType(Enum):
    """Enumeration for terminal types"""
    ATM = 'A'  # Caixa Automático
    POS = 'B'  # Pagamento Automático
    EMPRESA = 'E'  # Terminal Empresa
    INTERNET = 'I'  # Internet
    BANCO = 'L'  # Host do Banco
    TELEVINTI4 = 'M'  # Televinti4
    QUIOSQUE = 'N'  # Quiosques

    @classmethod
    def from_code(cls, code: str) -> 'TerminalType':
        try:
            return code
        except ValueError:
            raise MEPSValidationError(f"Invalid terminal type code: {code}")

@dataclass
class MEPSHeader:
    id: int
    tipreg: str
    fich: str
    idinstori: str
    idinstdes: str
    idfich: str
    idfichant: str
    entidade: str
    codmoeda: str
    taxaiva: Decimal
    idfichedst: str
    filename: str
    datetime: str

    def __post_init__(self):
        """Validate header data after initialization"""
        if self.tipreg != '0':
            raise MEPSValidationError("Invalid header record type")
        if self.fich != 'MEPS':
            raise MEPSValidationError("Invalid file type")
        try:
            self.taxaiva = Decimal(self.taxaiva)
        except:
            raise MEPSValidationError("Invalid VAT rate")

@dataclass
class MEPSDetail:
    id: int
    tipreg: str
    codproc: str
    idlog: str
    nrlog: str
    dthora: str
    montpgps: Decimal
    tarifaps: Decimal
    tipoterm: TerminalType
    idterminal: str
    identranps: str
    locmorter: str
    refpag: str
    modenv: str
    codresp: str
    nridresps: str
    version: int
    filename: str
    datetime: str

    @property
    def transaction_datetime(self) -> datetime:
        """Convert dthora string to datetime object"""
        try:
            return datetime.strptime(self.dthora, '%Y%m%d%H%M%S')
        except ValueError:
            raise MEPSValidationError(f"Invalid date/time format: {self.dthora}")

    @property
    def net_amount(self) -> Decimal:
        """Calculate net amount (montpgps - tarifaps)"""
        return self.montpgps - self.tarifaps

@dataclass
class MEPSTrailer:
    id: int
    tipreg: str
    totreg: int
    montranps: Decimal
    tottarps: Decimal
    valiva: Decimal
    entidade: str
    filename: str
    datetime: str

@dataclass
class MEPSFile:
    """Container for complete MEPS file data"""
    header: MEPSHeader
    details: List[MEPSDetail]
    trailer: MEPSTrailer

    def to_dict(self) -> Dict:
        """Convert the entire file to a dictionary"""
        return {
            'header': {k: str(v) for k, v in vars(self.header).items()},
            'details': [{k: str(v) for k, v in vars(d).items()} for d in self.details],
            'trailer': {k: str(v) for k, v in vars(self.trailer).items()}
        }

    def to_json(self) -> str:
        """Convert the file to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    def export_transactions_csv(self, output_path: Union[str, Path]) -> None:
        """Export transactions to CSV file"""
        fieldnames = [
            'reference', 'date', 'amount', 'fee', 'terminal_type',
            'terminal_id', 'location', 'net_amount'
        ]

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for detail in self.details:
                writer.writerow({
                    'id': self.header.id,
                    'reference': detail.refpag,
                    'date': detail.transaction_datetime.isoformat(),
                    'amount': detail.montpgps,
                    'fee': detail.tarifaps,
                    'terminal_type': detail.tipoterm.name,
                    'terminal_id': detail.idterminal,
                    'location': detail.locmorter,
                    'net_amount': detail.net_amount
                })

class MEPSFileParser:
    def __init__(self):
        self._reset()

    def _reset(self):
        """Reset parser state"""
        self.header: Optional[MEPSHeader] = None
        self.details: List[MEPSDetail] = []
        self.trailer: Optional[MEPSTrailer] = None

    @contextmanager
    def _error_context(self, context: str):
        """Context manager for error handling"""
        try:
            yield
        except MEPSError:
            raise
        except Exception as e:
            raise MEPSParsingError(f"Error in {context}: {str(e)}")

    def _parse_decimal(self, value: str, decimal_places: int = 2) -> Decimal:
        """Parse decimal value with proper scaling"""
        try:
            return Decimal(value.strip()) / Decimal(10 ** decimal_places)
        except:
            raise MEPSValidationError(f"Invalid decimal value: {value}")

    def parse_header(self, line: str, filename: str) -> MEPSHeader:
        """Parse header record (type 0)"""
        with self._error_context("header parsing"):
            return MEPSHeader(
                id=int(line[21:32] + line[46:51]),
                tipreg=line[0:1],
                fich=line[1:5].strip(),
                idinstori=line[5:13].strip(),
                idinstdes=line[13:21].strip(),
                idfich=line[21:32].strip(),
                idfichant=line[32:43].strip(),
                entidade=line[46:51].strip(),
                codmoeda=line[51:54].strip(),
                taxaiva=self._parse_decimal(line[54:57]),
                idfichedst=line[57:68].strip(),
                filename=os.path.basename(filename),
                datetime=datetime.now().strftime('%Y%m%d%H%M%S')
            )

    def parse_detail(self, line: str, filename: str) -> MEPSDetail:
        """Parse detail record (type 2)"""
        with self._error_context("detail parsing"):
            # Determine version based on line length
            version = 2 if len(line.strip()) >= 103 else 1

            # Common fields for both versions
            base_detail = {
                'id': int(line[3:7] + line[7:15]),
                'tipreg': line[0:1],
                'codproc': line[1:3].strip(),
                'idlog': line[3:7].strip(),
                'nrlog': line[7:15].strip(),
                'dthora': line[15:29].strip(),
                'montpgps': self._parse_decimal(line[29:39]),
                'version': version,
                'filename': os.path.basename(filename),
                'datetime': datetime.now().strftime('%Y%m%d%H%M%S')
            }

            # Version-specific parsing
            if version == 1:
                base_detail.update({
                    'tarifaps': self._parse_decimal(line[39:44]),
                    'tipoterm': TerminalType.from_code(line[44:45].strip()),
                    'idterminal': line[45:55].strip(),
                    'identranps': line[55:60].strip(),
                    'locmorter': line[60:75].strip(),
                    'refpag': line[75:84].strip(),
                    'modenv': line[84:85].strip(),
                    'codresp': line[85:86].strip(),
                    'nridresps': line[86:98].strip()
                })
            else:
                base_detail.update({
                    'tarifaps': self._parse_decimal(line[39:49]),
                    'tipoterm': TerminalType.from_code(line[49:50].strip()),
                    'idterminal': line[50:60].strip(),
                    'identranps': line[60:65].strip(),
                    'locmorter': line[65:80].strip(),
                    'refpag': line[80:89].strip(),
                    'modenv': line[89:90].strip(),
                    'codresp': line[90:91].strip(),
                    'nridresps': line[91:103].strip()
                })

            return MEPSDetail(**base_detail)

    def parse_trailer(self, line: str, filename: str) -> MEPSTrailer:
        """Parse trailer record (type 9)"""
        with self._error_context("trailer parsing"):

            # Extract the entidade_number from the filename
            filename_parts = filename.split("_")
            entidade_number = filename_parts[1]

            # Filename cleanup
            entidade = re.sub("^.*MEPS_|_.*$", "", filename)

            # Convert the entidade_number to an integer
            entidade_number = int(entidade_number)
            filename_dt = re.sub("^.*_(\d{14})_.*$", r"\1", filename)
            datetime_value = datetime.now().strftime('%Y%m%d%H%M%S')  # Current date

            return MEPSTrailer(
                id= int(filename_dt+str(entidade_number)),  # Assuming this is the primary key
                tipreg=line[0:1],
                totreg=int(line[1:9].strip()),
                montranps=self._parse_decimal(line[9:25]),
                tottarps=self._parse_decimal(line[25:37]),
                valiva=self._parse_decimal(line[37:49]),
                entidade=entidade,
                filename=filename,
                datetime=datetime_value
            )

    def parse_file(self, file_path: Union[str, Path]) -> MEPSFile:
        """Parse complete MEPS file"""
        self._reset()
        logger.info(f"Starting to parse file: {file_path}")

        with self._error_context("file parsing"):

            # Extract filename
            filename = Path(file_path).stem

            with open(file_path, 'r', encoding='utf-8') as file:
                for line_number, line in enumerate(file, 1):
                    if not line.strip():
                        continue

                    record_type = line[0:1]
                    logger.debug(f"Processing line {line_number}, record type {record_type}")

                    try:
                        if record_type == '0':
                            self.header = self.parse_header(line, filename)
                        elif record_type == '2':
                            self.details.append(self.parse_detail(line, filename))
                        elif record_type == '9':
                            self.trailer = self.parse_trailer(line, filename)
                        else:
                            raise MEPSValidationError(f"Invalid record type: {record_type}")
                    except Exception as e:
                        raise MEPSParsingError(f"Error on line {line_number}: {str(e)}")

            # Validate file structure
            self._validate_file()

            logger.info("File parsing completed successfully")

            return MEPSFile(
                header=self.header,
                details=self.details,
                trailer=self.trailer
            )

    def _validate_file(self):
        """Validate file structure and contents"""
        with self._error_context("file validation"):
            if not self.header:
                raise MEPSValidationError("Missing header record")
            if not self.trailer:
                raise MEPSValidationError("Missing trailer record")
            if not self.details:
                raise MEPSValidationError("No detail records found")

            # Validate record count
            if len(self.details) != self.trailer.totreg:
                raise MEPSValidationError(
                    f"Record count mismatch. Expected {self.trailer.totreg}, got {len(self.details)}"
                )

            # Validate total amounts
            total_montpgps = sum(detail.montpgps for detail in self.details)
            total_tarifaps = sum(detail.tarifaps for detail in self.details)

            expected_montranps = total_montpgps - total_tarifaps

            if abs(expected_montranps - self.trailer.montranps) > Decimal('0.01'):
                raise MEPSValidationError(
                    f"Amount mismatch. Expected {expected_montranps}, got {self.trailer.montranps}"
                )

            if abs(total_tarifaps - self.trailer.tottarps) > Decimal('0.01'):
                raise MEPSValidationError(
                    f"Fee mismatch. Expected {total_tarifaps}, got {self.trailer.tottarps}"
                )
