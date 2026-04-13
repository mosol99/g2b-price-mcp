"""
나라장터 가격정보현황서비스 MCP Server
======================================
조달청 나라장터의 시설공통자재 및 시장시공가격 정보를 
Claude에서 대화형으로 검색할 수 있는 MCP 서버입니다.

End Point: https://apis.data.go.kr/1230000/ao/PriceInfoService
"""

import os
import json
import httpx
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

# ─── 서버 초기화 ───────────────────────────────────────────
mcp = FastMCP("g2b_price_mcp")

# ─── 설정 ──────────────────────────────────────────────────
API_BASE_URL = "https://apis.data.go.kr/1230000/ao/PriceInfoService"
SERVICE_KEY = os.environ.get("G2B_SERVICE_KEY", "")
DEFAULT_NUM_OF_ROWS = 20
REQUEST_TIMEOUT = 30.0


# ─── 공통 유틸리티 ─────────────────────────────────────────
async def _make_api_request(operation: str, params: dict) -> dict:
    """조달청 API 공통 호출 함수"""
    url = f"{API_BASE_URL}/{operation}"
    
    # 기본 파라미터
    request_params = {
        "serviceKey": SERVICE_KEY,
        "type": "json",
        "numOfRows": str(params.pop("numOfRows", DEFAULT_NUM_OF_ROWS)),
        "pageNo": str(params.pop("pageNo", 1)),
    }
    
    # 사용자 파라미터 추가 (None 값 제외)
    for key, value in params.items():
        if value is not None and value != "":
            request_params[key] = str(value)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=request_params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()


def _handle_api_error(e: Exception) -> str:
    """일관된 에러 메시지 포맷팅"""
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 401:
            return "오류: 인증키가 유효하지 않습니다. G2B_SERVICE_KEY 환경변수를 확인하세요."
        elif status == 404:
            return "오류: API 엔드포인트를 찾을 수 없습니다."
        elif status == 429:
            return "오류: API 호출 한도를 초과했습니다. 잠시 후 다시 시도하세요."
        return f"오류: API 요청 실패 (HTTP {status})"
    elif isinstance(e, httpx.TimeoutException):
        return "오류: API 응답 시간 초과. 잠시 후 다시 시도하세요."
    elif isinstance(e, json.JSONDecodeError):
        return "오류: API 응답 형식이 올바르지 않습니다 (JSON 파싱 실패). 인증키를 확인하세요."
    return f"오류: {type(e).__name__} - {str(e)}"


def _extract_items(data: dict) -> list:
    """API 응답에서 아이템 목록 추출"""
    try:
        body = data.get("response", {}).get("body", {})
        items = body.get("items", [])
        total_count = body.get("totalCount", 0)
        
        if isinstance(items, list):
            return items, total_count
        elif isinstance(items, dict):
            # 단일 아이템인 경우
            return [items], total_count
        return [], 0
    except (AttributeError, TypeError):
        return [], 0


def _format_price(value) -> str:
    """가격 포맷팅 (천 단위 콤마)"""
    try:
        if value is None or value == "":
            return "-"
        num = float(value)
        if num == int(num):
            return f"{int(num):,}"
        return f"{num:,.2f}"
    except (ValueError, TypeError):
        return str(value)


# ─── 도구 입력 모델 ────────────────────────────────────────

class MaterialPriceInput(BaseModel):
    """시설공통자재 가격 조회 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    prdctClsfcNoNm: Optional[str] = Field(
        default=None,
        description="물품분류명 (예: '레미콘', '철근', '시멘트', '합판'). 검색하고자 하는 자재명 키워드."
    )
    # 가격업무구분: 토목/건축/기계설비/전기,정보통신/종합
    prtlPrcBsnsDivNm: Optional[str] = Field(
        default=None,
        description="가격업무구분명. '토목', '건축', '기계설비', '전기,정보통신', '종합' 중 선택."
    )
    inqryBgnDt: Optional[str] = Field(
        default=None,
        description="조회시작일 (형식: YYYYMMDD, 예: '20260101')"
    )
    inqryEndDt: Optional[str] = Field(
        default=None,
        description="조회종료일 (형식: YYYYMMDD, 예: '20260413')"
    )
    numOfRows: Optional[int] = Field(
        default=20,
        description="한 페이지 결과 수 (기본값: 20, 최대: 100)",
        ge=1, le=100
    )
    pageNo: Optional[int] = Field(
        default=1,
        description="페이지 번호 (기본값: 1)",
        ge=1
    )


class MarketPriceInput(BaseModel):
    """시장시공가격 조회 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    rsrcNm: Optional[str] = Field(
        default=None,
        description="자원명(공종명) 키워드 (예: '철근공', '콘크리트공', '미장공', '방수공')"
    )
    prtlPrcBsnsDivNm: Optional[str] = Field(
        default=None,
        description="가격업무구분명. '토목', '건축', '기계설비' 중 선택."
    )
    inqryBgnDt: Optional[str] = Field(
        default=None,
        description="조회시작일 (형식: YYYYMMDD)"
    )
    inqryEndDt: Optional[str] = Field(
        default=None,
        description="조회종료일 (형식: YYYYMMDD)"
    )
    numOfRows: Optional[int] = Field(default=20, ge=1, le=100)
    pageNo: Optional[int] = Field(default=1, ge=1)


class StandardPriceInput(BaseModel):
    """표준시장단가 및 시장시공가격 조회 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    stnrdMrktUntpcNm: Optional[str] = Field(
        default=None,
        description="표준시장단가명 키워드 (예: '보통인부', '특별인부', '비계공')"
    )
    inqryBgnDt: Optional[str] = Field(default=None, description="조회시작일 (YYYYMMDD)")
    inqryEndDt: Optional[str] = Field(default=None, description="조회종료일 (YYYYMMDD)")
    numOfRows: Optional[int] = Field(default=20, ge=1, le=100)
    pageNo: Optional[int] = Field(default=1, ge=1)


class ResourceClassInput(BaseModel):
    """자원분류 및 순수자원 조회 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    rsrcClsfcNm: Optional[str] = Field(
        default=None,
        description="자원분류명 키워드 (예: '노무비', '재료비', '경비')"
    )
    numOfRows: Optional[int] = Field(default=20, ge=1, le=100)
    pageNo: Optional[int] = Field(default=1, ge=1)


class WorkTypeInput(BaseModel):
    """공종분류 및 세부공종 조회 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    workTyClsfcNm: Optional[str] = Field(
        default=None,
        description="공종분류명 키워드 (예: '토공', '콘크리트공', '철근공', '포장공')"
    )
    numOfRows: Optional[int] = Field(default=20, ge=1, le=100)
    pageNo: Optional[int] = Field(default=1, ge=1)


# ─── MCP 도구 정의 ─────────────────────────────────────────

@mcp.tool(
    name="g2b_search_material_price",
    annotations={
        "title": "시설공통자재 가격 검색",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def search_material_price(params: MaterialPriceInput) -> str:
    """조달청 나라장터의 시설공통자재(토목/건축/기계설비/전기,정보통신/종합) 가격정보를 검색합니다.
    
    레미콘, 철근, 시멘트, 합판, 배관 등 건설자재의 조달청 고시 가격을 조회할 수 있습니다.
    교정시설 BTL 등 시설공사의 설계 참고가격으로 활용됩니다.
    
    Args:
        params: 물품분류명, 가격업무구분, 조회기간 등 검색 조건
    
    Returns:
        자재별 가격, 단위, 공급지역, 게시일자 등 가격정보 목록
    """
    try:
        request_params = params.model_dump(exclude_none=True)
        data = await _make_api_request("getCmnMtrlPriceInfo", request_params)
        items, total_count = _extract_items(data)
        
        if not items:
            return f"검색 결과가 없습니다. 검색 조건을 변경해 보세요.\n(검색조건: {json.dumps(params.model_dump(exclude_none=True), ensure_ascii=False)})"
        
        # 마크다운 포맷 응답
        lines = [f"## 시설공통자재 가격정보 (총 {total_count}건 중 {len(items)}건)\n"]
        
        for i, item in enumerate(items, 1):
            lines.append(f"### {i}. {item.get('prdctClsfcNoNm', '(품명 없음)')}")
            lines.append(f"- **물품식별번호**: {item.get('prdctIdntNoNm', '-')}")
            lines.append(f"- **가격**: {_format_price(item.get('prc', '-'))}원")
            lines.append(f"- **단위**: {item.get('unt', '-')}")
            lines.append(f"- **공급지역**: {item.get('splyJrsdctnAreaNm', '-')}")
            lines.append(f"- **인도조건**: {item.get('dlvryCndtnNm', '-')}")
            lines.append(f"- **업무구분**: {item.get('prtlPrcBsnsDivNm', '-')}")
            lines.append(f"- **게시일자**: {item.get('ntcDt', '-')}")
            lines.append(f"- **부가세포함**: {item.get('vatYn', '-')}")
            lines.append("")
        
        if total_count > len(items):
            lines.append(f"\n> 📌 전체 {total_count}건 중 {len(items)}건 표시. 다음 페이지는 pageNo={params.pageNo + 1}로 조회하세요.")
        
        return "\n".join(lines)
    
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="g2b_search_market_construction_price",
    annotations={
        "title": "시장시공가격 검색",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def search_market_construction_price(params: MarketPriceInput) -> str:
    """조달청 나라장터의 시장시공가격(토목/건축/기계설비)을 검색합니다.
    
    철근공, 콘크리트공, 미장공, 방수공 등 각 공종별 시장시공가격을 조회합니다.
    실제 시장에서 거래되는 시공 단가를 파악하는 데 활용됩니다.
    
    Args:
        params: 자원명(공종명), 가격업무구분, 조회기간 등 검색 조건
    
    Returns:
        공종별 시장시공가격, 단위, 규격 등 가격정보 목록
    """
    try:
        request_params = params.model_dump(exclude_none=True)
        data = await _make_api_request("getMrktCnstrcPriceInfo", request_params)
        items, total_count = _extract_items(data)
        
        if not items:
            return f"검색 결과가 없습니다. 검색 조건을 변경해 보세요."
        
        lines = [f"## 시장시공가격 정보 (총 {total_count}건 중 {len(items)}건)\n"]
        
        for i, item in enumerate(items, 1):
            lines.append(f"### {i}. {item.get('rsrcNm', '(공종명 없음)')}")
            lines.append(f"- **가격**: {_format_price(item.get('prc', '-'))}원")
            lines.append(f"- **단위**: {item.get('unt', '-')}")
            lines.append(f"- **규격**: {item.get('spcfctn', '-')}")
            lines.append(f"- **업무구분**: {item.get('prtlPrcBsnsDivNm', '-')}")
            lines.append(f"- **게시일자**: {item.get('ntcDt', '-')}")
            lines.append("")
        
        if total_count > len(items):
            lines.append(f"\n> 📌 전체 {total_count}건 중 {len(items)}건 표시.")
        
        return "\n".join(lines)
    
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="g2b_search_standard_market_price",
    annotations={
        "title": "표준시장단가 검색",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def search_standard_market_price(params: StandardPriceInput) -> str:
    """조달청의 표준시장단가 및 시장시공가격을 검색합니다.
    
    보통인부, 특별인부, 비계공 등 노무비 단가와 표준시장단가를 조회합니다.
    공사비 산정의 기초 자료로 활용됩니다.
    
    Args:
        params: 표준시장단가명, 조회기간 등 검색 조건
    
    Returns:
        표준시장단가명, 가격, 단위, 규격 등 정보 목록
    """
    try:
        request_params = params.model_dump(exclude_none=True)
        data = await _make_api_request("getStnrdMrktUntpcAndMrktCnstrcPriceInfo", request_params)
        items, total_count = _extract_items(data)
        
        if not items:
            return "검색 결과가 없습니다."
        
        lines = [f"## 표준시장단가 정보 (총 {total_count}건 중 {len(items)}건)\n"]
        
        for i, item in enumerate(items, 1):
            lines.append(f"### {i}. {item.get('stnrdMrktUntpcNm', '(명칭 없음)')}")
            lines.append(f"- **가격**: {_format_price(item.get('prc', '-'))}원")
            lines.append(f"- **단위**: {item.get('unt', '-')}")
            lines.append(f"- **규격**: {item.get('spcfctn', '-')}")
            lines.append(f"- **게시일자**: {item.get('ntcDt', '-')}")
            lines.append("")
        
        return "\n".join(lines)
    
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="g2b_search_resource_class",
    annotations={
        "title": "자원분류 및 순수자원 검색",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def search_resource_class(params: ResourceClassInput) -> str:
    """조달청의 자원분류 및 순수자원 정보를 검색합니다.
    
    노무비, 재료비, 경비 등 공사비 구성요소의 자원 분류 체계를 조회합니다.
    
    Args:
        params: 자원분류명 등 검색 조건
    
    Returns:
        자원분류 코드, 명칭, 단위 등 정보 목록
    """
    try:
        request_params = params.model_dump(exclude_none=True)
        data = await _make_api_request("getRsrcClsfcAndPureRsrcInfo", request_params)
        items, total_count = _extract_items(data)
        
        if not items:
            return "검색 결과가 없습니다."
        
        lines = [f"## 자원분류 정보 (총 {total_count}건 중 {len(items)}건)\n"]
        
        for i, item in enumerate(items, 1):
            lines.append(f"### {i}. {item.get('rsrcClsfcNm', '(분류명 없음)')}")
            lines.append(f"- **자원코드**: {item.get('rsrcClsfcNo', '-')}")
            lines.append(f"- **단위**: {item.get('unt', '-')}")
            lines.append(f"- **규격**: {item.get('spcfctn', '-')}")
            lines.append("")
        
        return "\n".join(lines)
    
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="g2b_search_work_type",
    annotations={
        "title": "공종분류 및 세부공종 검색",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def search_work_type(params: WorkTypeInput) -> str:
    """조달청의 공종분류 및 세부공종 정보를 검색합니다.
    
    토공, 콘크리트공, 철근공, 포장공 등 건설공사의 공종 분류 체계를 조회합니다.
    
    Args:
        params: 공종분류명 등 검색 조건
    
    Returns:
        공종분류 코드, 명칭, 세부공종 등 정보 목록
    """
    try:
        request_params = params.model_dump(exclude_none=True)
        data = await _make_api_request("getWorkTyClsfcAndDetailWorkTyInfo", request_params)
        items, total_count = _extract_items(data)
        
        if not items:
            return "검색 결과가 없습니다."
        
        lines = [f"## 공종분류 정보 (총 {total_count}건 중 {len(items)}건)\n"]
        
        for i, item in enumerate(items, 1):
            lines.append(f"### {i}. {item.get('workTyClsfcNm', '(공종명 없음)')}")
            lines.append(f"- **공종코드**: {item.get('workTyClsfcNo', '-')}")
            lines.append(f"- **세부공종**: {item.get('detailWorkTyNm', '-')}")
            lines.append("")
        
        return "\n".join(lines)
    
    except Exception as e:
        return _handle_api_error(e)


# ─── 서버 실행 ─────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
