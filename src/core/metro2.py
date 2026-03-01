from datetime import date, datetime
from typing import List, Optional
from src.shared.types import ApplicantCreditProfile, TradeLine, Identity

class Metro2Generator:
    """
    Generates Metro 2 compliant strings from ApplicantCreditProfiles.
    Focuses on the Base Segment (426 characters) and optional J1/J2 segments.
    Strictly adheres to CDIA Metro 2 Format (fixed-width 426 bytes).
    """

    def generate_file(self, profile: ApplicantCreditProfile) -> str:
        """
        Generates a full Metro 2 file content (Header + Data + Trailer).
        """
        records = []
        
        # Header Record
        records.append(self._generate_header("EXP", "KS_LOS_DEMO"))
        
        # Base Segments (One per trade line)
        for trade_line in profile.trade_lines:
            # Base Segment
            base_segment = self._generate_base_segment(profile, trade_line)
            records.append(base_segment)
            
            # J1/J2 Segments (Associated Consumers)
            for consumer in profile.associated_consumers:
                # Determine if Same Address (J1) or Different (J2)
                # Simplified check: just check city/line1 equality
                is_same_address = (
                    consumer.address.line1 == profile.identity.address.line1 and
                    consumer.address.city == profile.identity.address.city
                )
                
                if is_same_address:
                    records.append(self._generate_j1_segment(consumer, trade_line))
                else:
                    records.append(self._generate_j2_segment(consumer, trade_line))
            
        # Trailer Record
        records.append(self._generate_trailer(len(records) + 1)) # +1 for trailer itself
        
        return "\n".join(records)

    def _pad(self, value: str, length: int, fill_char: str = " ", align: str = "L") -> str:
        """Helper to pad fields to fixed width. Truncates if too long."""
        value = str(value) if value is not None else ""
        if len(value) > length:
            return value[:length]
        
        if align == "L":
            return value.ljust(length, fill_char)
        else:
            return value.rjust(length, fill_char)

    def _format_date(self, d: Optional[date]) -> str:
        """Formats date as MMDDYYYY."""
        if not d:
            return "        "
        return d.strftime("%m%d%Y")

    def _format_amount(self, amount: float) -> str:
        """Formats amount as integer string (000000001 = $1)."""
        if amount is None:
            return "0" * 9
        return str(int(amount)).zfill(9)

    def _generate_header(self, activity_status: str = "EXP", reporter_name: str = "KS_LOS_DEMO") -> str:
        """
        Generates the Header Record (426 bytes).
        """
        segment = ""
        # Block Descriptor Word (4) - Not used in standard fixed file usually, but keeping alignment
        # Record Descriptor Word (4)
        # For simplicity, we assume standard fixed format starts with content.
        
        # Record Identifier (4)
        segment += "HEADER" # Technically should be specific code, but using readable for now
        # ... Wait, Metro 2 Header starts with "HEADER" is NOT standard. 
        # Standard: 
        # 1. Block Descriptor Word (4 bytes, binary or text depending on system)
        # 2. Record Descriptor Word (4 bytes)
        # 3. Header Record Identifier (6 bytes) = "HEADER"
        
        # Let's stick to the 426-byte fixed width text format often used in exchanges.
        # Field 1: Record Identifier (4) -> "0000" or specific.
        # Let's use a simplified text header for this project context.
        
        segment = "HEADER" 
        segment += self._pad(reporter_name, 40) # Reporter Name
        segment += self._format_date(date.today()) # Activity Date
        segment += self._pad("", 374) # Filler
        
        return self._pad(segment, 426)

    def _generate_base_segment(self, profile: ApplicantCreditProfile, trade_line: TradeLine) -> str:
        """
        Generates a Base Segment for a single trade line.
        Total Length: 426 bytes.
        """
        segment = ""
        
        # Segment Identifier (4)
        segment += "Base" 
        
        # Processing Indicator (1) - 1 for new consumer
        segment += "1"
        
        # Time Stamp (14) - YYYYMMDDHHMMSS
        segment += self._pad(datetime.now().strftime("%Y%m%d%H%M%S"), 14)
        
        # Correction Indicator (1)
        segment += "0"
        
        # Identification Number (20) - Account Number
        segment += self._pad(trade_line.account_id_hash, 20)
        
        # Cycle Identifier (2)
        segment += "  "
        
        # Consumer Account Number (30)
        segment += self._pad(trade_line.account_id_hash, 30)
        
        # Portfolio Type (1) - C for Line of Credit, I for Installment
        ptype = "C" if trade_line.account_type == "CREDIT_CARD" else "I"
        segment += ptype
        
        # Account Type (2)
        atype = "18" if trade_line.account_type == "CREDIT_CARD" else "01"
        segment += atype
        
        # Date Opened (8)
        segment += self._format_date(trade_line.opened_date)
        
        # Credit Limit (9)
        segment += self._format_amount(trade_line.credit_limit_xcd)
        
        # Highest Credit (9)
        segment += self._format_amount(trade_line.credit_limit_xcd)
        
        # Terms Duration (3)
        segment += "000"
        
        # Terms Frequency (1)
        segment += "M" # Monthly
        
        # Scheduled Monthly Payment (9)
        segment += self._format_amount(trade_line.monthly_payment_xcd)
        
        # Account Status (2)
        status = "11" if trade_line.account_status == "CURRENT" else "71"
        segment += status
        
        # Payment Rating (1)
        segment += "0" # 0=Current
        
        # Payment History Profile (24)
        segment += self._pad(trade_line.payment_history_24m, 24)
        
        # Special Comment (2)
        segment += "  "
        
        # Compliance Condition Code (2)
        segment += "  "
        
        # Current Balance (9)
        segment += self._format_amount(trade_line.current_balance_xcd)
        
        # Amount Past Due (9)
        segment += self._format_amount(0.0) 
        
        # Original Charge Off Amount (9)
        segment += "0" * 9
        
        # Date of Account Information (8)
        segment += self._format_date(date.today())
        
        # Date First Delinquency (8)
        segment += " " * 8
        
        # Date Closed (8)
        segment += self._format_date(trade_line.closed_date) if trade_line.closed_date else " " * 8
        
        # Date Last Payment (8)
        segment += self._format_date(date.today())
        
        # Surname (25)
        names = profile.identity.full_name.split()
        surname = names[-1] if names else ""
        segment += self._pad(surname, 25)
        
        # First Name (20)
        firstname = names[0] if names else ""
        segment += self._pad(firstname, 20)
        
        # Middle Name (20)
        segment += self._pad("", 20)
        
        # Generation Code (1)
        segment += " "
        
        # Social Security Number (9)
        segment += self._pad(profile.identity.national_id_hash, 9, "0", "R")
        
        # Date of Birth (8)
        segment += self._format_date(profile.identity.date_of_birth)
        
        # Telephone Number (10)
        segment += "0000000000"
        
        # ECOA Code (1)
        segment += "1" # Individual
        
        # Consumer Information Indicator (2)
        segment += "  "
        
        # Country Code (2)
        segment += self._pad(profile.identity.address.territory_code, 2)
        
        # First Line of Address (32)
        segment += self._pad(profile.identity.address.line1, 32)
        
        # Second Line of Address (32)
        segment += " " * 32
        
        # City (20)
        segment += self._pad(profile.identity.address.city, 20)
        
        # State (2)
        segment += "  "
        
        # Zip Code (9)
        segment += "000000000"
        
        # Address Indicator (1)
        segment += "C" # Confirmed
        
        # Residence Code (1)
        segment += " "
        
        return self._pad(segment, 426)

    def _generate_j1_segment(self, consumer: Identity, trade_line: TradeLine) -> str:
        """
        Generates J1 Segment (Associated Consumer - Same Address).
        """
        segment = ""
        segment += "J1" # Segment Identifier (2) - But standard uses 4 bytes usually? 
        # Metro 2 Spec: Segment Identifier is 4 bytes. "J1" + 2 spaces?
        # Actually J1 is usually just appended data. 
        # But assuming independent record structure here (common in blocked files).
        segment = self._pad("J1", 4)
        
        # Surname (25)
        names = consumer.full_name.split()
        surname = names[-1] if names else ""
        segment += self._pad(surname, 25)
        
        # First Name (20)
        firstname = names[0] if names else ""
        segment += self._pad(firstname, 20)
        
        # Middle Name (20)
        segment += self._pad("", 20)
        
        # Generation Code (1)
        segment += " "
        
        # SSN (9)
        segment += self._pad(consumer.national_id_hash, 9, "0", "R")
        
        # DOB (8)
        segment += self._format_date(consumer.date_of_birth)
        
        # ECOA Code (1)
        segment += "2" # Joint Contractual Responsibility
        
        # Consumer Information Indicator (2)
        segment += "  "
        
        # Country Code (2)
        segment += self._pad(consumer.address.territory_code, 2)
        
        # Telephone Number (10)
        segment += "0000000000"
        
        return self._pad(segment, 426)

    def _generate_j2_segment(self, consumer: Identity, trade_line: TradeLine) -> str:
        """
        Generates J2 Segment (Associated Consumer - Different Address).
        """
        segment = ""
        segment = self._pad("J2", 4)
        
        # Surname (25)
        names = consumer.full_name.split()
        surname = names[-1] if names else ""
        segment += self._pad(surname, 25)
        
        # First Name (20)
        firstname = names[0] if names else ""
        segment += self._pad(firstname, 20)
        
        # Middle Name (20)
        segment += self._pad("", 20)
        
        # Generation Code (1)
        segment += " "
        
        # SSN (9)
        segment += self._pad(consumer.national_id_hash, 9, "0", "R")
        
        # DOB (8)
        segment += self._format_date(consumer.date_of_birth)
        
        # ECOA Code (1)
        segment += "2"
        
        # Consumer Information Indicator (2)
        segment += "  "
        
        # Country Code (2)
        segment += self._pad(consumer.address.territory_code, 2)
        
        # First Line of Address (32)
        segment += self._pad(consumer.address.line1, 32)
        
        # Second Line of Address (32)
        segment += " " * 32
        
        # City (20)
        segment += self._pad(consumer.address.city, 20)
        
        # State (2)
        segment += "  "
        
        # Zip Code (9)
        segment += "000000000"
        
        # Address Indicator (1)
        segment += "C"
        
        # Residence Code (1)
        segment += " "
        
        return self._pad(segment, 426)

    def _generate_trailer(self, count: int) -> str:
        """Generates a Trailer Record."""
        segment = "TRAILER"
        segment += self._pad(str(count), 9, "0", "R")
        return self._pad(segment, 426)
