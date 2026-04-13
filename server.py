import os
os.environ["FASTMCP_HOST"] = "0.0.0.0"
os.environ["FASTMCP_PORT"] = "8000"
"""
나라장터 가격정보현황서비스 MCP Server
End Point: https://apis.data.go.kr/1230000/ao/PriceInfoService
"""

import json
import httpx
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("g2b_price_mcp", host="0.0.0.0", port=8000)

API_BASE_URL = "https://apis.data.go.kr/1230000/ao/PriceInfoService"
SERVICE_KEY = os.environ.get("G2B_SERVICE_KEY", "")

async def _api(op: str, params: dict) -> dict:
    url = f"{API_BASE_URL}/{op}"
    p = {"serviceKey": SERVICE_KEY, "type": "json",
         "numOfRows": str(params.pop("numOfRows", 20)),
         "pageNo": str(params.pop("pageNo", 1))}
    for k, v in params.items():
        if v is not None and v != "":
            p[k] = str(v)
    async with httpx.AsyncClient() as c:
        r = await c.get(url, params=p, timeout=30.0)
        r.raise_for_status()
        return r.json()

def _items(data):
    try:
        body = data.get("response", {}).get("body", {})
        items = body.get("items", [])
        total = body.get("totalCount", 0)
        if isinstance(items, list): return items, total
        if isinstance(items, dict): return [items], total
        return [], 0
    except: return [], 0

def _fp(v):
    try:
        if not v or v == "": return "-"
        n = float(v)
        return f"{int(n):,}" if n == int(n) else f"{n:,.2f}"
    except: return str(v)

def _fmt(items, total, title):
    lines = [f"## {title} (총 {total}건 중 {len(items)}건)\n"]
    for i, item in enumerate(items, 1):
        nm = item.get('prdctClsfcNoNm', item.get('prdnm', '(품명 없음)'))
        lines.append(f"### {i}. {nm}")
        for k, l in [('prdctIdntNoNm','물품식별'),('spcNm','규격'),('prc','가격'),('unt','단위'),('splyJrsdctnAreaNm','공급지역'),('dlvryCndtnNm','인도조건'),('ntcDt','게시일자')]:
            v = item.get(k)
            if v:
                lines.append(f"- **{l}**: {_fp(v)+'원' if k=='prc' else v}")
        lines.append("")
    return "\n".join(lines)

class S(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    prdctClsfcNo: Optional[str] = Field(default=None, description="물품분류번호")
    prdnm: Optional[str] = Field(default=None, description="품명 키워드 (예: 레미콘, 철근, 시멘트)")
    prdctIdntNo: Optional[str] = Field(default=None, description="물품식별번호")
    spcNm: Optional[str] = Field(default=None, description="규격명")
    numOfRows: Optional[int] = Field(default=20, ge=1, le=100)
    pageNo: Optional[int] = Field(default=1, ge=1)

class W(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    cnsttyClsfcCd: Optional[str] = Field(default=None, description="공사분류코드")
    prdnm: Optional[str] = Field(default=None, description="품명 키워드")
    numOfRows: Optional[int] = Field(default=20, ge=1, le=100)
    pageNo: Optional[int] = Field(default=1, ge=1)

@mcp.tool(name="g2b_material_total")
async def t1(p: S) -> str:
    """시설공통자재(종합) 가격 검색. 토목/건축/기계설비/전기통신 전체 자재 가격을 조회합니다."""
    try:
        d = await _api("getPriceInfoListFcltyCmmnMtrilTotal", p.model_dump(exclude_none=True))
        i, t = _items(d)
        return _fmt(i, t, "시설공통자재(종합)") if i else "검색 결과 없음"
    except Exception as e: return str(e)

@mcp.tool(name="g2b_material_civil")
async def t2(p: S) -> str:
    """시설공통자재(토목) 가격 검색"""
    try:
        d = await _api("getPriceInfoListFcltyCmmnMtrilEngrk", p.model_dump(exclude_none=True))
        i, t = _items(d)
        return _fmt(i, t, "시설공통자재(토목)") if i else "검색 결과 없음"
    except Exception as e: return str(e)

@mcp.tool(name="g2b_material_building")
async def t3(p: S) -> str:
    """시설공통자재(건축) 가격 검색"""
    try:
        d = await _api("getPriceInfoListFcltyCmmnMtrilBildng", p.model_dump(exclude_none=True))
        i, t = _items(d)
        return _fmt(i, t, "시설공통자재(건축)") if i else "검색 결과 없음"
    except Exception as e: return str(e)

@mcp.tool(name="g2b_material_mechanical")
async def t4(p: S) -> str:
    """시설공통자재(기계설비) 가격 검색"""
    try:
        d = await _api("getPriceInfoListFcltyCmmnMtrilMchnEqp", p.model_dump(exclude_none=True))
        i, t = _items(d)
        return _fmt(i, t, "시설공통자재(기계설비)") if i else "검색 결과 없음"
    except Exception as e: return str(e)

@mcp.tool(name="g2b_material_electrical")
async def t5(p: S) -> str:
    """시설공통자재(전기,정보통신) 가격 검색"""
    try:
        d = await _api("getPriceInfoListFcltyCmmnMtrilElctyIrmc", p.model_dump(exclude_none=True))
        i, t = _items(d)
        return _fmt(i, t, "시설공통자재(전기,정보통신)") if i else "검색 결과 없음"
    except Exception as e: return str(e)

@mcp.tool(name="g2b_market_civil")
async def t6(p: S) -> str:
    """시장시공가격(토목) 검색"""
    try:
        d = await _api("getPriceInfoListMrktCnstrctPcEngrk", p.model_dump(exclude_none=True))
        i, t = _items(d)
        return _fmt(i, t, "시장시공가격(토목)") if i else "검색 결과 없음"
    except Exception as e: return str(e)

@mcp.tool(name="g2b_market_building")
async def t7(p: S) -> str:
    """시장시공가격(건축) 검색"""
    try:
        d = await _api("getPriceInfoListMrktCnstrctPcBildng", p.model_dump(exclude_none=True))
        i, t = _items(d)
        return _fmt(i, t, "시장시공가격(건축)") if i else "검색 결과 없음"
    except Exception as e: return str(e)

@mcp.tool(name="g2b_market_mechanical")
async def t8(p: S) -> str:
    """시장시공가격(기계설비) 검색"""
    try:
        d = await _api("getPriceInfoListMrktCnstrctPcMchnEqp", p.model_dump(exclude_none=True))
        i, t = _items(d)
        return _fmt(i, t, "시장시공가격(기계설비)") if i else "검색 결과 없음"
    except Exception as e: return str(e)

@mcp.tool(name="g2b_work_type")
async def t9(p: W) -> str:
    """공종분류 및 세부공종 검색"""
    try:
        d = await _api("getCnsttyClsfcInfoList", p.model_dump(exclude_none=True))
        i, t = _items(d)
        if not i: return "검색 결과 없음"
        lines = [f"## 공종분류 (총 {t}건 중 {len(i)}건)\n"]
        for n, item in enumerate(i, 1):
            lines.append(f"{n}. {item.get('qtyCalcCdNm', '-')} (코드: {item.get('qtyCalcCd', '-')})")
        return "\n".join(lines)
    except Exception as e: return str(e)

@mcp.tool(name="g2b_std_market_price")
async def t10(p: W) -> str:
    """표준시장단가 검색. 세부공종별 재료비/노무비/경비 합계를 조회합니다."""
    try:
        d = await _api("getStdMarkUprcinfoList", p.model_dump(exclude_none=True))
        i, t = _items(d)
        if not i: return "검색 결과 없음"
        lines = [f"## 표준시장단가 (총 {t}건 중 {len(i)}건)\n"]
        for n, item in enumerate(i, 1):
            lines.append(f"### {n}. {item.get('prdnm', '-')}")
            for k, l in [('spcNm','규격'),('unt','단위'),('mtrilCost','재료비'),('lbrCost','노무비'),('expns','경비'),('totAmt','합계')]:
                v = item.get(k)
                if v: lines.append(f"- **{l}**: {_fp(v)+'원' if 'Cost' in k or k in ('expns','totAmt') else v}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e: return str(e)

@mcp.tool(name="g2b_resource")
async def t11(p: S) -> str:
    """자원분류 및 순수자원 검색"""
    try:
        d = await _api("getNetRsceinfoList", p.model_dump(exclude_none=True))
        i, t = _items(d)
        return _fmt(i, t, "자원분류") if i else "검색 결과 없음"
    except Exception as e: return str(e)

# ASGI app for uvicorn

if __name__ == "__main__":
    mcp.run(transport="sse")
