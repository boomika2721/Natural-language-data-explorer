import json
import sys
import io
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
from app import app

def test_all_features():
    client = app.test_client()
    
    print("=" * 65)
    print("NLDE Integration & Enhanced Feature Test Suite")
    print("=" * 65)

    # 1. Base Endpoints & Auth
    print("\n1. Testing Core Endpoints...")
    res = client.get('/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    
    # Login as demo user
    login_res = client.post('/login', data={"email": "demo@nlde.com", "password": "Demo@123"})
    assert login_res.status_code in (200, 302)

    res = client.get('/analytics')
    assert res.status_code == 200
    analytics_data = json.loads(res.data)
    assert analytics_data["success"] is True
    print("  -> Passed /analytics (Students count:", analytics_data["data"]["total_students"], ")")

    # 2. Test Existing Students Queries (English, Tamil, Typos)
    print("\n2. Testing Natural Language Queries on Students...")
    queries = [
        ("Show all students", 120),
        ("Show students from Erode", 27),
        ("Students with CGPA above 8", 78),
        ("Count students department wise", 7),
        ("Average CGPA", 1),
        ("Highest CGPA", 1),
        ("மாணவர்களை காட்டு", 120),
        ("studnts from erod", 27)
    ]
    for q, exp_rows in queries:
        res = client.post('/query', json={"query": q, "table": "students"})
        assert res.status_code == 200
        q_data = json.loads(res.data)
        assert q_data["success"] is True
        assert q_data["row_count"] == exp_rows, f"Failed for '{q}': expected {exp_rows}, got {q_data['row_count']}"
        print(f"  -> '{q}' -> {q_data['row_count']} rows | SQL: {q_data['sql_query']}")

    # 3. Test Security Whitelist
    print("\n3. Testing Security Protection...")
    unsafe = client.post('/query', json={"query": "DROP TABLE students;", "table": "students"})
    assert unsafe.status_code == 403
    print("  -> Security Passed: Unsafe query blocked with 403.")

    # 4. Test Dynamic Dataset Upload (CSV)
    print("\n4. Testing Dynamic Dataset Upload (CSV)...")
    csv_data = (
        "product_id,product_name,category,unit_price,units_sold,revenue\n"
        "101,Quantum Laptop,Electronics,1200,45,54000\n"
        "102,Ergo Chair,Furniture,250,80,20000\n"
        "103,Wireless Mouse,Electronics,35,320,11200\n"
        "104,Standing Desk,Furniture,450,40,18000\n"
        "105,Noise Cancelling Headphones,Electronics,180,110,19800\n"
        "106,Mechanical Keyboard,Electronics,95,150,14250\n"
        "107,Monitor Arm,Furniture,65,90,5850\n"
        "108,UltraWide Monitor,Electronics,600,30,18000\n"
    )
    data = {
        'file': (io.BytesIO(csv_data.encode('utf-8')), 'sales_data.csv'),
        'table_name': 'test_sales'
    }
    upload_res = client.post('/datasets/upload', data=data, content_type='multipart/form-data')
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.data}"
    up_json = json.loads(upload_res.data)
    assert up_json["success"] is True
    tbl = up_json["table_name"]
    assert "test_sales" in tbl
    assert up_json["rows"] == 8
    print(f"  -> Dataset Uploaded successfully ({tbl})! Rows:", up_json["rows"], "Cols:", len(up_json["columns"]))
    print("  -> AI Summary generated:", up_json["ai_summary"][:120], "...")

    # 5. Test Dataset Preview
    print("\n5. Testing Dataset Preview...")
    prev_res = client.get(f'/datasets/{tbl}/preview')
    assert prev_res.status_code == 200
    prev_json = json.loads(prev_res.data)
    assert len(prev_json["rows"]) == 8
    print("  -> Preview verified: 8 rows returned.")

    # 6. Test Data Profiling
    print("\n6. Testing Automatic Data Profiling...")
    prof_res = client.get(f'/datasets/{tbl}/profile')
    assert prof_res.status_code == 200
    prof_json = json.loads(prof_res.data)
    assert prof_json["profile"]["total_rows"] == 8
    assert prof_json["profile"]["total_columns"] == 6
    assert prof_json["profile"]["null_percentage"] == 0.0
    print("  -> Data Profiling verified: 0% missing, 6 columns profiled.")

    # 7. Test Predictive Analytics (Regression & Correlation)
    print("\n7. Testing Predictive Analytics...")
    pred_res = client.get(f'/datasets/{tbl}/predictive')
    assert pred_res.status_code == 200
    pred_json = json.loads(pred_res.data)
    assert pred_json["predictive"]["has_numeric"] is True
    assert "regression" in pred_json["predictive"]
    eq = pred_json["predictive"]["regression"]["equation"]
    print(f"  -> Predictive Analytics fitted: {eq}")
    print(f"  -> Insight: {pred_json['predictive']['regression']['narrative']}")

    # 8. Test Universal Natural Language Queries on Uploaded Dataset
    print(f"\n8. Testing Universal NLP Querying on Uploaded Dataset ({tbl})...")
    sales_queries = [
        ("Show all records", 8),
        ("Average unit price", 1),
        ("Highest revenue", 1),
        ("Category wise count", 2),
        ("Top 3 products", 3)
    ]
    for sq, exp in sales_queries:
        res = client.post('/query', json={"query": sq, "table": tbl})
        assert res.status_code == 200, f"Query '{sq}' failed: {res.data}"
        sq_json = json.loads(res.data)
        assert sq_json["success"] is True
        print(f"  -> [{tbl}] '{sq}' -> SQL: {sq_json['sql_query']} ({sq_json['row_count']} rows)")

    # 9. Test Dataset Comparison
    print("\n9. Testing Dataset Comparison...")
    comp_res = client.post('/datasets/compare', json={"table1": "students", "table2": tbl})
    assert comp_res.status_code == 200
    comp_json = json.loads(comp_res.data)
    assert comp_json["success"] is True
    print("  -> Dataset comparison completed successfully.")
    print("     Students rows:", comp_json["comparison"]["dataset_1"]["rows"], f"| {tbl} rows:", comp_json["comparison"]["dataset_2"]["rows"])

    # 10. Test Dataset Rename
    print("\n10. Testing Dataset Rename...")
    ren_res = client.post(f'/datasets/{tbl}/rename', json={"new_name": "renamed_sales"})
    assert ren_res.status_code == 200
    ren_json = json.loads(ren_res.data)
    renamed_tbl = ren_json["new_table"]
    print(f"  -> Renamed {tbl} -> {renamed_tbl} successfully.")

    # 11. Test Dataset Deletion
    print("\n11. Testing Dataset Deletion...")
    del_res = client.delete(f'/datasets/{renamed_tbl}')
    assert del_res.status_code == 200
    print(f"  -> Deleted {renamed_tbl} successfully.")

    print("\n" + "=" * 65)
    print("ALL 100% OF TESTS (ORIGINAL & ENHANCED) PASSED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == '__main__':
    test_all_features()
