from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

auction_price = 10000
top_bidder: str | None = None          # 현재 최고 입찰자

connections: dict[WebSocket, str] = {}      # 접속자 목록 {연결: 이름}

# 입찰 참여, 퇴장시 실행 함수
async def broadcast(message: dict, exclude: WebSocket | None = None):
    for ws in list(connections):        # list()로 복사: 도는 중에 목록이 바뀌어도 안전
        # 현재 ws(접속중인 유저)가 제외 대상이면 건너뜀
        if ws is exclude:
            continue

        try:
            await ws.send_json(message)
        except Exception:
            connections.pop(ws, None)       # 보내기 실패 = 이미 끝난 연결이니 정리


async def handle_bid(websocket: WebSocket, name: str, price):
    global auction_price, top_bidder        # 이게 없으면 전역변수 변경 불가
    
    # 1) 검증: 숫자인가?
    if not isinstance(price, int):
        await websocket.send_json({"type": "error", "message": "숫자를 입력하세요"})
        return

    # 2) 검증: 현재가보다 높은가?
    if price <= auction_price:
        await websocket.send_json({
            "type": "error",
            "message": f"현재가 {auction_price:,}원보다 높게 입찰하세요",
        })
        return

    # 3) 통과 → 갱신 후 모두에게 알림 (입찰한 본인 포함)
    auction_price = price
    top_bidder = name
    print(f"{name} 입찰: {price:,}원")

    await broadcast({"type": "price", "price": auction_price, "bidder": top_bidder})


@app.websocket("/ws")
async def auction_websocket(websocket: WebSocket, name: str):
    await websocket.accept()      # 연결 수락. 이게 없으면 클라이언트 연결 불가

    # 1) 기존 접속자들에게 먼저 알림 (아직 목록에 안 넣었으니 본인은 자연스럽게 제외됨)
    await broadcast({"type": "join", "name": name})

    # 2) 목록에 추가
    connections[websocket] = name
    print(f"{name} 접속 (현재 {len(connections)}명)")

    # 연결시 현재 가격을 보내줌
    await websocket.send_json({"type": "price", "price": auction_price, "bidder": top_bidder})

    try:
        while True:         # 연결이 살아있는 동안 계속 반복
            data = await websocket.receive_json()   # 메시지 올때까지 대기 (await)

            if data.get("type") == "bid":
                await handle_bid(websocket, name, data.get("price"))
    # 클라이언트가 연결을 닫으면 발생하는 예외
    except WebSocketDisconnect:
        # 4) 나가면 목록에서 빼고, 남은 사람들에게 알림
        connections.pop(websocket, None)
        await broadcast({"type": "leave", "name": name})
        print(f"{name} 퇴장 (현재 {len(connections)}명)")