"""
엑셀 파싱 엔진
- 엑셀/CSV 파일 읽기
- 컬럼 자동 감지
- 거래 및 주식 매매 데이터 임포트
"""
import json
import re
from datetime import datetime

import pandas as pd

from database import db_session
from models.transaction import Transaction
from models.stock import Stock, StockTrade
from services.person_matcher import find_or_create_person


def parse_excel(filepath: str, sheet_name=None) -> pd.DataFrame:
    """
    엑셀/CSV 파일을 파싱하여 DataFrame으로 반환

    Args:
        filepath: 파일 경로
        sheet_name: 시트 이름 (None이면 첫 번째 시트)

    Returns:
        pandas DataFrame
    """
    if filepath.lower().endswith(".csv"):
        # CSV: 여러 인코딩 시도
        for encoding in ["utf-8", "cp949", "euc-kr", "utf-8-sig"]:
            try:
                df = pd.read_csv(filepath, encoding=encoding)
                return df
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError("CSV 파일 인코딩을 인식할 수 없습니다.")
    else:
        # 엑셀
        kwargs = {}
        if sheet_name is not None:
            kwargs["sheet_name"] = sheet_name
        df = pd.read_excel(filepath, **kwargs)
        return df


def get_sheet_names(filepath: str) -> list:
    """엑셀 파일의 시트 이름 목록 반환"""
    if filepath.lower().endswith(".csv"):
        return []
    xls = pd.ExcelFile(filepath)
    return xls.sheet_names


def detect_columns(df: pd.DataFrame) -> dict:
    """
    각 컬럼의 데이터 타입을 추론

    Returns:
        {컬럼명: {type: 'date'|'number'|'text', sample: 샘플값, suggestion: 추천매핑}}
    """
    result = {}
    # 추천 매핑을 위한 키워드
    date_keywords = ["날짜", "일자", "date", "일시", "거래일"]
    amount_keywords = ["금액", "amount", "입금", "출금", "거래금액", "잔액"]
    type_keywords = ["구분", "type", "입출금", "거래종류", "종류"]
    name_keywords = ["예금자", "이름", "성명", "name", "상대방", "거래처", "보낸분", "받는분"]
    desc_keywords = ["적요", "메모", "비고", "내용", "description", "memo"]
    stock_keywords = ["종목", "stock", "주식"]
    qty_keywords = ["수량", "quantity", "주수"]
    price_keywords = ["단가", "price", "가격"]
    fee_keywords = ["수수료", "fee"]
    tax_keywords = ["세금", "tax"]

    for col in df.columns:
        col_str = str(col).strip()
        col_lower = col_str.lower()
        sample_values = df[col].dropna().head(5).tolist()
        sample = str(sample_values[0]) if sample_values else ""

        # 타입 추론
        col_type = _infer_column_type(df[col])

        # 추천 매핑
        suggestion = None
        if any(kw in col_lower for kw in date_keywords) or col_type == "date":
            suggestion = "date_col"
        elif any(kw in col_lower for kw in name_keywords):
            suggestion = "counterparty_col"
        elif any(kw in col_lower for kw in type_keywords):
            suggestion = "type_col"
        elif any(kw in col_lower for kw in desc_keywords):
            suggestion = "description_col"
        elif any(kw in col_lower for kw in stock_keywords):
            suggestion = "stock_name_col"
        elif any(kw in col_lower for kw in qty_keywords):
            suggestion = "quantity_col"
        elif any(kw in col_lower for kw in price_keywords):
            suggestion = "price_col"
        elif any(kw in col_lower for kw in fee_keywords):
            suggestion = "fee_col"
        elif any(kw in col_lower for kw in tax_keywords):
            suggestion = "tax_col"
        elif any(kw in col_lower for kw in amount_keywords):
            suggestion = "amount_col"

        result[col_str] = {
            "type": col_type,
            "sample": sample,
            "suggestion": suggestion,
        }

    return result


def _infer_column_type(series: pd.Series) -> str:
    """컬럼 데이터 타입 추론"""
    non_null = series.dropna()
    if non_null.empty:
        return "text"

    # 이미 datetime 타입인 경우
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"

    # 숫자형인 경우
    if pd.api.types.is_numeric_dtype(series):
        return "number"

    # 문자열 샘플로 판단
    samples = non_null.head(10).astype(str)

    # 날짜 패턴 검사
    date_patterns = [
        r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",  # 2024-01-01, 2024/01/01
        r"^\d{8}$",  # 20240101
    ]
    date_matches = sum(
        1
        for s in samples
        if any(re.match(p, s.strip()) for p in date_patterns)
    )
    if date_matches >= len(samples) * 0.5:
        return "date"

    # 숫자 패턴 검사 (콤마 포함)
    num_pattern = r"^-?[\d,]+\.?\d*$"
    num_matches = sum(
        1 for s in samples if re.match(num_pattern, s.strip().replace(" ", ""))
    )
    if num_matches >= len(samples) * 0.5:
        return "number"

    return "text"


def _parse_date(value) -> datetime | None:
    """
    다양한 형식의 날짜를 파싱

    지원 형식: 2024-01-01, 2024/01/01, 20240101, 2024.01.01 등
    """
    if pd.isna(value):
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    s = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y%m%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y.%m.%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    # pandas fallback
    try:
        return pd.to_datetime(s).to_pydatetime()
    except Exception:
        return None


def _parse_amount(value) -> int | None:
    """
    금액 문자열을 정수로 변환
    콤마 제거, 음수 처리, 괄호 표기 처리
    """
    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return int(value)

    s = str(value).strip()

    # 괄호 표기 음수: (1,000) -> -1000
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]

    # 콤마, 공백, 원 기호 제거
    s = s.replace(",", "").replace(" ", "").replace("원", "").replace("₩", "")

    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def import_transactions(
    df: pd.DataFrame,
    column_mapping: dict,
    account_id: int,
    session_id: int,
) -> dict:
    """
    DataFrame의 거래 데이터를 DB에 임포트

    Args:
        df: 파싱된 DataFrame
        column_mapping: 컬럼 매핑 정보
            - date_col: 날짜 컬럼명
            - amount_col: 금액 컬럼명
            - type_col: 입출금 구분 컬럼명 (선택)
            - counterparty_col: 예금자명 컬럼명 (선택)
            - description_col: 적요 컬럼명 (선택)
            - deposit_col: 입금 컬럼명 (금액이 입금/출금 분리된 경우)
            - withdrawal_col: 출금 컬럼명 (금액이 입금/출금 분리된 경우)
        account_id: 계좌 ID
        session_id: 업로드 세션 ID

    Returns:
        {imported: int, skipped: int, errors: list}
    """
    imported = 0
    skipped = 0
    errors = []

    date_col = column_mapping.get("date_col")
    amount_col = column_mapping.get("amount_col")
    type_col = column_mapping.get("type_col")
    counterparty_col = column_mapping.get("counterparty_col")
    description_col = column_mapping.get("description_col")
    deposit_col = column_mapping.get("deposit_col")
    withdrawal_col = column_mapping.get("withdrawal_col")

    if not date_col:
        return {"imported": 0, "skipped": 0, "errors": ["날짜 컬럼이 지정되지 않았습니다."]}

    # 입금/출금 분리 컬럼이 없으면 금액+구분 컬럼 필요
    has_split_cols = deposit_col and withdrawal_col
    if not has_split_cols and not amount_col:
        return {
            "imported": 0,
            "skipped": 0,
            "errors": ["금액 컬럼 또는 입금/출금 컬럼이 지정되지 않았습니다."],
        }

    for idx, row in df.iterrows():
        row_num = idx + 2  # 엑셀 기준 행 번호 (헤더 제외)
        try:
            # 날짜 파싱
            tx_date = _parse_date(row.get(date_col))
            if tx_date is None:
                skipped += 1
                errors.append(f"행 {row_num}: 날짜 파싱 실패 ({row.get(date_col)})")
                continue

            # 금액 및 타입 결정
            if has_split_cols:
                dep_val = _parse_amount(row.get(deposit_col))
                wdr_val = _parse_amount(row.get(withdrawal_col))
                if dep_val and dep_val > 0:
                    amount = dep_val
                    tx_type = "deposit"
                elif wdr_val and wdr_val > 0:
                    amount = wdr_val
                    tx_type = "withdrawal"
                else:
                    skipped += 1
                    errors.append(f"행 {row_num}: 입금/출금 금액을 파싱할 수 없음")
                    continue
            else:
                amount = _parse_amount(row.get(amount_col))
                if amount is None:
                    skipped += 1
                    errors.append(f"행 {row_num}: 금액 파싱 실패 ({row.get(amount_col)})")
                    continue

                # 타입 결정
                if type_col and pd.notna(row.get(type_col)):
                    raw_type = str(row.get(type_col)).strip()
                    if raw_type in ("입금", "deposit", "입", "수입", "IN"):
                        tx_type = "deposit"
                    elif raw_type in ("출금", "withdrawal", "출", "지출", "OUT"):
                        tx_type = "withdrawal"
                    else:
                        # 금액 부호로 판단
                        tx_type = "deposit" if amount >= 0 else "withdrawal"
                else:
                    tx_type = "deposit" if amount >= 0 else "withdrawal"

                amount = abs(amount)

            if amount == 0:
                skipped += 1
                continue

            # 예금자명
            counterparty_raw = ""
            if counterparty_col and pd.notna(row.get(counterparty_col)):
                counterparty_raw = str(row.get(counterparty_col)).strip()

            # 적요
            description = None
            if description_col and pd.notna(row.get(description_col)):
                description = str(row.get(description_col)).strip()

            # 인물 매칭
            person_id = None
            alias_id = None
            if counterparty_raw:
                person_id, alias_id = find_or_create_person(counterparty_raw)

            # 원본 데이터 JSON
            raw_data = json.dumps(
                {str(k): str(v) for k, v in row.to_dict().items() if pd.notna(v)},
                ensure_ascii=False,
            )

            tx = Transaction(
                account_id=account_id,
                person_alias_id=alias_id,
                person_id=person_id,
                upload_session_id=session_id,
                transaction_date=tx_date,
                type=tx_type,
                amount=amount,
                counterparty_raw=counterparty_raw,
                description=description,
                raw_data=raw_data,
            )
            db_session.add(tx)
            imported += 1

        except Exception as e:
            skipped += 1
            errors.append(f"행 {row_num}: {str(e)}")

    db_session.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors}


def import_stock_trades(
    df: pd.DataFrame,
    column_mapping: dict,
    account_id: int,
    session_id: int,
) -> dict:
    """
    DataFrame의 주식 매매 데이터를 DB에 임포트

    Args:
        df: 파싱된 DataFrame
        column_mapping: 컬럼 매핑 정보
            - date_col: 날짜 컬럼명
            - stock_name_col: 종목명 컬럼명
            - stock_code_col: 종목코드 컬럼명 (선택)
            - type_col: 매수/매도 구분 컬럼명
            - quantity_col: 수량 컬럼명
            - price_col: 단가 컬럼명
            - amount_col: 총 금액 컬럼명 (선택, 없으면 수량*단가)
            - fee_col: 수수료 컬럼명 (선택)
            - tax_col: 세금 컬럼명 (선택)
        account_id: 계좌 ID
        session_id: 업로드 세션 ID

    Returns:
        {imported: int, skipped: int, errors: list}
    """
    imported = 0
    skipped = 0
    errors = []

    date_col = column_mapping.get("date_col")
    stock_name_col = column_mapping.get("stock_name_col")
    stock_code_col = column_mapping.get("stock_code_col")
    type_col = column_mapping.get("type_col")
    quantity_col = column_mapping.get("quantity_col")
    price_col = column_mapping.get("price_col")
    amount_col = column_mapping.get("amount_col")
    fee_col = column_mapping.get("fee_col")
    tax_col = column_mapping.get("tax_col")

    # 필수 컬럼 체크
    missing = []
    if not date_col:
        missing.append("날짜")
    if not stock_name_col:
        missing.append("종목명")
    if not quantity_col:
        missing.append("수량")
    if not price_col and not amount_col:
        missing.append("단가 또는 총 금액")
    if missing:
        return {
            "imported": 0,
            "skipped": 0,
            "errors": [f"필수 컬럼이 지정되지 않았습니다: {', '.join(missing)}"],
        }

    # 종목 캐시 (이름 -> Stock 객체)
    stock_cache = {}

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            # 날짜
            trade_date = _parse_date(row.get(date_col))
            if trade_date is None:
                skipped += 1
                errors.append(f"행 {row_num}: 날짜 파싱 실패")
                continue

            # 종목명
            stock_name = str(row.get(stock_name_col, "")).strip()
            if not stock_name:
                skipped += 1
                errors.append(f"행 {row_num}: 종목명 없음")
                continue

            stock_code = None
            if stock_code_col and pd.notna(row.get(stock_code_col)):
                stock_code = str(row.get(stock_code_col)).strip()

            # 종목 찾거나 생성
            if stock_name not in stock_cache:
                stock = (
                    db_session.query(Stock).filter(Stock.name == stock_name).first()
                )
                if not stock:
                    stock = Stock(name=stock_name, code=stock_code)
                    db_session.add(stock)
                    db_session.flush()
                stock_cache[stock_name] = stock
            stock = stock_cache[stock_name]

            # 매매 구분
            if type_col and pd.notna(row.get(type_col)):
                raw_type = str(row.get(type_col)).strip()
                if raw_type in ("매수", "buy", "BUY", "Buy", "매입"):
                    trade_type = "buy"
                elif raw_type in ("매도", "sell", "SELL", "Sell"):
                    trade_type = "sell"
                else:
                    trade_type = "buy"  # 기본값
            else:
                trade_type = "buy"

            # 수량
            quantity = _parse_amount(row.get(quantity_col)) if quantity_col else None
            if not quantity or quantity <= 0:
                skipped += 1
                errors.append(f"행 {row_num}: 수량이 유효하지 않음")
                continue

            # 단가
            price_per_unit = _parse_amount(row.get(price_col)) if price_col else 0

            # 총 금액
            if amount_col and pd.notna(row.get(amount_col)):
                total_amount = _parse_amount(row.get(amount_col))
            else:
                total_amount = (price_per_unit or 0) * quantity

            if total_amount is None:
                total_amount = 0

            # 수수료, 세금
            fee = _parse_amount(row.get(fee_col)) if fee_col else 0
            tax = _parse_amount(row.get(tax_col)) if tax_col else 0
            fee = fee or 0
            tax = tax or 0

            # 원본 데이터
            raw_data = json.dumps(
                {str(k): str(v) for k, v in row.to_dict().items() if pd.notna(v)},
                ensure_ascii=False,
            )

            trade = StockTrade(
                account_id=account_id,
                stock_id=stock.id,
                upload_session_id=session_id,
                trade_date=trade_date,
                type=trade_type,
                quantity=quantity,
                price_per_unit=price_per_unit or 0,
                total_amount=total_amount,
                fee=fee,
                tax=tax,
                raw_data=raw_data,
            )
            db_session.add(trade)
            imported += 1

        except Exception as e:
            skipped += 1
            errors.append(f"행 {row_num}: {str(e)}")

    db_session.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors}
