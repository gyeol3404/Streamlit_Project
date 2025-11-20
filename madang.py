import streamlit as st
import duckdb
import pandas as pd
import time

# --- 데이터베이스 연결 설정 ---
# madang.db 파일이 같은 폴더에 있어야 합니다.
# read_only=False로 설정하여 데이터 입력/수정이 가능하게 합니다.
db_path = 'madang.db'
con = duckdb.connect(database=db_path, read_only=False)

# 쿼리 실행 도우미 함수
def query(sql, params=None):
    try:
        if params:
            # DuckDB 파라미터 바인딩 (?)
            df = con.execute(sql, params).df()
        else:
            df = con.execute(sql).df()
        
        return df.to_dict('records')
    except Exception as e:
        # 에러 발생 시 화면에 표시하지 않고 빈 리스트 반환 (혹은 필요시 st.error로 출력)
        # st.error(f"Query Error: {e}")
        return []

# --- Streamlit UI 시작 ---

st.title("마당서점 관리 시스템 (DuckDB)")

# 초기 도서 목록 로드
books = [] 
try:
    result = query("SELECT concat(bookid, ',', bookname) AS book_info FROM Book")
    for res in result:
        books.append(res['book_info'])
except Exception as e:
    st.error("데이터베이스 연결 오류: madang.db 파일이 있는지 확인해주세요.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["고객조회", "거래 입력", "신규 고객 추가"])

# --- Tab 1: 고객 조회 ---
with tab1:
    st.header("고객 정보 조회")
    name = st.text_input("고객명 검색", key="cust_name_input")
    
    if name:
        sql_customer = "SELECT * FROM Customer WHERE name = ?"
        customer_data = query(sql_customer, [name])
        
        if customer_data:
            cust_df = pd.DataFrame(customer_data)
            st.subheader("1. 고객 정보")
            st.dataframe(cust_df)
            
            current_cust = customer_data[0]
            st.session_state['current_custid'] = current_cust['custid']
            st.session_state['current_name'] = current_cust['name']
            
            st.subheader("2. 과거 주문 내역")
            sql_history = """
                SELECT o.orderid, b.bookname, o.saleprice, o.orderdate
                FROM Orders o
                JOIN Book b ON o.bookid = b.bookid
                WHERE o.custid = ?
                ORDER BY o.orderdate DESC
            """
            history_data = query(sql_history, [current_cust['custid']])
            
            if history_data:
                st.dataframe(pd.DataFrame(history_data))
            else:
                st.info("과거 주문 내역이 없는 신규 고객입니다.")
                
        else:
            st.warning("해당 이름의 고객을 찾을 수 없습니다.")
            if 'current_custid' in st.session_state:
                del st.session_state['current_custid']
                del st.session_state['current_name']

# --- Tab 2: 거래 입력 ---
with tab2:
    st.header("신규 거래 입력")
    
    if 'current_custid' in st.session_state:
        current_custid = st.session_state['current_custid']
        current_name = st.session_state['current_name']

        st.success(f"선택된 고객: {current_name} (ID: {current_custid})")

        select_book = st.selectbox("구매 서적 선택:", books)
        price = st.text_input("판매 금액 (원)")

        if st.button('거래 입력'):
            if select_book and price:
                try:
                    bookid = int(select_book.split(",")[0])
                    dt = time.strftime('%Y-%m-%d', time.localtime())
                    
                    # OrderID 생성
                    max_res = query("SELECT max(orderid) as max_id FROM Orders")
                    if not max_res or pd.isna(max_res[0]['max_id']):
                        orderid = 1
                    else:
                        orderid = int(max_res[0]['max_id']) + 1

                    sql = """
                        INSERT INTO Orders (orderid, custid, bookid, saleprice, orderdate) 
                        VALUES (?, ?, ?, ?, ?)
                    """
                    con.execute(sql, [orderid, current_custid, bookid, int(price), dt])
                    
                    st.balloons()
                    st.success(f"거래가 성공적으로 입력되었습니다. (주문번호: {orderid})")
                    
                except Exception as e:
                    st.error(f"에러 발생: {e}")
            else:
                st.error("금액을 입력해주세요.")
    else:
        st.info("👈 '고객조회' 탭에서 고객을 먼저 검색해주세요.")

# --- Tab 3: 신규 고객 추가 ---
with tab3:
    st.header("신규 고객 등록")
    new_name = st.text_input("고객명")
    new_address = st.text_input("주소")
    new_phone = st.text_input("전화번호")
    
    if st.button("고객 등록"):
        if new_name:
            try:
                max_cust_res = query("SELECT max(custid) as max_id FROM Customer")
                if not max_cust_res or pd.isna(max_cust_res[0]['max_id']):
                    new_custid = 1
                else:
                    new_custid = int(max_cust_res[0]['max_id']) + 1
                    
                sql_new_cust = "INSERT INTO Customer (custid, name, address, phone) VALUES (?, ?, ?, ?)"
                con.execute(sql_new_cust, [new_custid, new_name, new_address, new_phone])
                
                st.success(f"{new_name} 고객님이 등록되었습니다.")
            except Exception as e:
                st.error(f"등록 실패: {e}")
        else:
            st.warning("고객명을 입력해주세요.")