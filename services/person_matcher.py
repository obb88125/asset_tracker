"""
예금자명 매칭 서비스
- 예금자명으로 인물 찾기/생성
- 인물 합치기 (merge)
- 별칭 분리 (split)
"""
from database import db_session
from models.person import Person, PersonAlias
from models.transaction import Transaction


def find_or_create_person(counterparty_name: str) -> tuple[int | None, int | None]:
    """
    예금자명으로 기존 인물을 찾거나 새로 생성

    Args:
        counterparty_name: 원본 예금자명

    Returns:
        (person_id, alias_id) 튜플
    """
    if not counterparty_name or not counterparty_name.strip():
        return None, None

    name = counterparty_name.strip()

    # 기존 별칭에서 정확히 일치하는 것 검색
    alias = (
        db_session.query(PersonAlias)
        .filter(PersonAlias.alias_name == name)
        .first()
    )

    if alias:
        return alias.person_id, alias.id

    # 없으면 새 Person + PersonAlias 생성
    person = Person(display_name=name)
    db_session.add(person)
    db_session.flush()  # ID 할당

    alias = PersonAlias(person_id=person.id, alias_name=name)
    db_session.add(alias)
    db_session.flush()

    return person.id, alias.id


def merge_persons(source_ids: list[int], target_id: int) -> dict:
    """
    여러 인물을 target으로 합치기

    source 인물들의 별칭과 거래를 target으로 이전한 뒤,
    source 인물들을 삭제한다.

    Args:
        source_ids: 합칠 원본 인물 ID 목록
        target_id: 대상 인물 ID

    Returns:
        {merged_count: int, aliases_moved: int, transactions_moved: int}
    """
    target = db_session.query(Person).get(target_id)
    if not target:
        raise ValueError(f"대상 인물(ID={target_id})을 찾을 수 없습니다.")

    aliases_moved = 0
    transactions_moved = 0
    merged_count = 0

    for source_id in source_ids:
        if source_id == target_id:
            continue

        source = db_session.query(Person).get(source_id)
        if not source:
            continue

        # 별칭 이전
        for alias in source.aliases:
            alias.person_id = target_id
            aliases_moved += 1

        # 거래 이전
        txs = (
            db_session.query(Transaction)
            .filter(Transaction.person_id == source_id)
            .all()
        )
        for tx in txs:
            tx.person_id = target_id
            transactions_moved += 1

        # source 인물 삭제 (별칭은 이미 이전했으므로 cascade 대상 없음)
        db_session.delete(source)
        merged_count += 1

    db_session.commit()

    return {
        "merged_count": merged_count,
        "aliases_moved": aliases_moved,
        "transactions_moved": transactions_moved,
    }


def split_alias(person_id: int, alias_id: int) -> dict:
    """
    별칭을 분리하여 새 인물 생성

    해당 별칭과 그에 연결된 거래를 새 인물로 이전한다.

    Args:
        person_id: 원본 인물 ID
        alias_id: 분리할 별칭 ID

    Returns:
        {new_person_id: int, transactions_moved: int}
    """
    alias = db_session.query(PersonAlias).get(alias_id)
    if not alias:
        raise ValueError(f"별칭(ID={alias_id})을 찾을 수 없습니다.")

    if alias.person_id != person_id:
        raise ValueError("해당 별칭은 지정된 인물에 속하지 않습니다.")

    # 원본 인물의 별칭이 1개뿐이면 분리 불가
    original = db_session.query(Person).get(person_id)
    if not original:
        raise ValueError(f"인물(ID={person_id})을 찾을 수 없습니다.")

    if len(original.aliases) <= 1:
        raise ValueError("별칭이 하나뿐인 인물에서는 분리할 수 없습니다.")

    # 새 인물 생성
    new_person = Person(display_name=alias.alias_name)
    db_session.add(new_person)
    db_session.flush()

    # 별칭 이전
    alias.person_id = new_person.id

    # 해당 별칭에 연결된 거래 이전
    txs = (
        db_session.query(Transaction)
        .filter(Transaction.person_alias_id == alias_id)
        .all()
    )
    transactions_moved = 0
    for tx in txs:
        tx.person_id = new_person.id
        transactions_moved += 1

    db_session.commit()

    return {
        "new_person_id": new_person.id,
        "transactions_moved": transactions_moved,
    }
