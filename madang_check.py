import pandas as pd
import streamlit as st
import time
import pymysql

# 1. 🚨 st.secrets를 사용하여 DB 연결 정보를 가져옵니다.
#    이 코드는 .streamlit/secrets.toml 파일의 [mysql] 섹션을 읽어옵니다.
db_config = st.secrets["mysql"] 

# 2. DB 연결 실행
#    secrets.toml 파일에서 가져온 정보를 사용하여 연결합니다.
dbConn = pymysql.connect(
    user=db_config["user"], 
    passwd=db_config["password"], 
    host=db_config["host"], 
    db=db_config["database"],
    charset='utf8'
)
cursor = dbConn.cursor(pymysql.cursors.DictCursor) # 커서 생성
# ... (이후의 모든 Streamlit 로직이 시작됩니다)
# ---------------------------------------------------------
# [초기화] Streamlit 세션 상태 설정
# ---------------------------------------------------------
# Streamlit이 재실행될 때 cu`stid와 name을 유지하기 위해 session_state 사용
if 'current_custid' not in st.session_state:
    st.session_state['current_custid'] = None
if 'current_name' not in st.session_state:
    st.session_state['current_name'] = ""

# ---------------------------------------------------------
# [함수] DB에서 책 목록 가져오기
# ---------------------------------------------------------
def fetch_books():
    cursor.execute("SELECT concat(bookid, ',', bookname) FROM Book")
    result = cursor.fetchall()
    books_list = [list(res.values())[0] for res in result]
    books_list.insert(0, None)
    return books_list

st.title("마당서점 고객 관리")

# 탭 구분
tab1, tab2 = st.tabs(["고객 관리", "거래 입력"])

# ---------------------------------------------------------
# [Tab 1] 고객 조회 및 신규 등록
# ---------------------------------------------------------
with tab1:
    name = st.text_input("고객명 입력", key="search_name")
    
    # 세션 상태에서 current_custid 가져오기 
    current_custid = st.session_state['current_custid']
    current_name = st.session_state['current_name']

    if name:
        # 1단계: 고객 테이블(Customer)에 이 사람이 있는지 확인
        sql_check = f"SELECT * FROM Customer WHERE name = '{name}'"
        cursor.execute(sql_check)
        customer_data = cursor.fetchall()
        df_customer = pd.DataFrame(customer_data)

        # 2단계: 분기 처리
        if df_customer.empty:
            # [Case A] 없는 사람 -> 신규 등록 기능 노출
            st.warning(f"'{name}' 고객님은 등록되지 않았습니다.")
            st.info("신규 고객으로 등록하시겠습니까?")
            
            with st.form("register_form"):
                if name == "이한결":
                    new_addr = st.text_input("주소", value="인천광역시 미추홀구 인하로 100")
                    new_phone = st.text_input("전화번호", value="01012345678")
                else:
                    new_addr = st.text_input("주소")
                    new_phone = st.text_input("전화번호")
                
                if st.form_submit_button("신규 등록"):
                    cursor.execute("SELECT MAX(custid) FROM Customer")
                    max_val = cursor.fetchone()
                    try:
                        new_id = list(max_val.values())[0] + 1
                    except:
                        new_id = 1 

                    insert_sql = f"INSERT INTO Customer(custid, name, address, phone) VALUES ({new_id}, '{name}', '{new_addr}', '{new_phone}')"
                    
                    try:
                        cursor.execute(insert_sql)
                        dbConn.commit()
                        st.success(f"{name} 고객 등록 완료! (ID: {new_id})")
                        st.session_state['current_custid'] = new_id
                        st.session_state['current_name'] = name
                    except Exception as e:
                        st.error(f"등록 실패: {e}")

        else:
            # [Case B] 있는 사람 -> 거래 내역 보여주기
            st.success(f"'{name}' 고객님을 찾았습니다.")
            
            st.session_state['current_custid'] = df_customer['custid'][0]
            st.session_state['current_name'] = name

            history_sql = f"""
                SELECT orderid, c.name, b.bookname, o.orderdate, o.saleprice 
                FROM Customer c, Book b, Orders o 
                WHERE c.custid = o.custid AND o.bookid = b.bookid AND c.name = '{name}'
            """
            cursor.execute(history_sql)
            history_df = pd.DataFrame(cursor.fetchall())
            st.write("거래 내역:", history_df)
    
    if not name:
        st.session_state['current_custid'] = None
        st.session_state['current_name'] = ""

# ---------------------------------------------------------
# [Tab 2] 거래 입력 및 삭제 기능 추가
# ---------------------------------------------------------
with tab2:
    current_custid = st.session_state['current_custid']
    current_name = st.session_state['current_name']
    
    if current_custid is None:
        st.warning("먼저 '고객 관리' 탭에서 고객을 검색하거나 등록해주세요.")
    else:
        st.write(f"고객명: {current_name} (고객번호: {current_custid})")
        
        # --- 1. 거래 입력 섹션 ---
        st.subheader("🛍️ 새 거래 입력")
        books = fetch_books() 
        select_book = st.selectbox("구매 서적:", books, key="purchase_book")
        price = st.text_input("판매 금액", key="purchase_price")
        
        if st.button("거래 입력", key="add_transaction"):
            if select_book is None or price == "":
                st.error("서적을 선택하고 판매 금액을 입력해주세요.")
            else:
                bookid = select_book.split(",")[0]
                dt = time.strftime('%Y-%m-%d', time.localtime())
                
                cursor.execute("SELECT MAX(orderid) FROM Orders")
                res = cursor.fetchone()
                try:
                    max_id_val = list(res.values())[0]
                    orderid = max_id_val + 1 if max_id_val is not None else 1
                except:
                    orderid = 1
                    
                order_sql = f"INSERT INTO Orders(orderid, custid, bookid, saleprice, orderdate) VALUES ({orderid}, {current_custid}, {bookid}, {price}, '{dt}')"
                
                try:
                    cursor.execute(order_sql)
                    dbConn.commit()
                    st.success("거래가 입력되었습니다. '고객 관리' 탭에서 확인해주세요.")
                except Exception as e:
                    st.error(f"거래 입력 실패: {e}")

        st.markdown("---")
        
        # --- 2. 거래 삭제 섹션 (추가된 기능) ---
        st.subheader("🗑️ 거래 삭제")
        
        delete_id = st.number_input(
            "삭제할 주문 번호(orderid) 입력:", 
            min_value=1, 
            step=1, 
            format="%i", 
            key="delete_order_id"
        )
        
        if st.button("선택 거래 삭제", key="delete_transaction"):
            if delete_id:
                # DELETE SQL 쿼리 실행
                delete_sql = f"DELETE FROM Orders WHERE orderid = {delete_id}"
                
                try:
                    cursor.execute(delete_sql)
                    dbConn.commit()
                    
                    # 삭제 후 상태 업데이트를 위해 session_state 초기화 (고객 관리 탭 재조회 유도)
                    st.session_state['current_custid'] = None
                    st.session_state['current_name'] = ""
                    
                    st.success(f"주문 번호 {delete_id}의 거래가 삭제되었습니다. '고객 관리' 탭에서 다시 조회해주세요.")
                    
                except Exception as e:
                    st.error(f"삭제 실패: 해당 주문 번호가 없거나 오류 발생: {e}")
            else:
                st.warning("유효한 주문 번호를 입력해주세요.")
