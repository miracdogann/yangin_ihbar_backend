#!/usr/bin/env python3
"""
Manuel Güvenlik Testleri - Derinlemesine Saldırı Simülasyonu
"""

import requests
import json
import sqlite3
import os

class AdvancedSecurityTester:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_direct_database_access(self):
        """Veritabanına doğrudan erişim testi"""
        print("🔍 Veritabanı Dosyası Analizi...")
        
        db_path = "db.sqlite3"
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Tablo listesi
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print(f"📊 Bulunan tablolar: {[table[0] for table in tables]}")
                
                # User tablosu analizi
                if ('yisis_app_user',) in tables:
                    cursor.execute("SELECT COUNT(*) FROM yisis_app_user")
                    user_count = cursor.fetchone()[0]
                    print(f"👥 Toplam kullanıcı sayısı: {user_count}")
                    
                    # İlk 3 kullanıcının bilgilerini al (sadece ID ve email)
                    cursor.execute("SELECT id, email, user_name_surname FROM yisis_app_user LIMIT 3")
                    users = cursor.fetchall()
                    print("📝 Örnek kullanıcılar:")
                    for user in users:
                        print(f"  ID: {user[0]}, Email: {user[1]}, Name: {user[2]}")
                
                # SecurityLog tablosu
                if ('yisis_app_securitylog',) in tables:
                    cursor.execute("SELECT COUNT(*) FROM yisis_app_securitylog")
                    log_count = cursor.fetchone()[0]
                    print(f"🔒 Güvenlik log sayısı: {log_count}")
                
                conn.close()
                
            except Exception as e:
                print(f"❌ Veritabanı erişim hatası: {e}")
        else:
            print("❌ Veritabanı dosyası bulunamadı")
    
    def test_authentication_flow(self):
        """Kimlik doğrulama akışını test et"""
        print("\n🔐 Kimlik Doğrulama Akışı Testi...")
        
        # 1. Geçerli kullanıcı kaydı
        user_data = {
            "name_surname": "Security Test User",
            "phone_number": "5551234567",
            "email": "sectest@test.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        
        print("📝 Kullanıcı kaydı testi...")
        response = self.session.post(f"{self.base_url}/api/register/", json=user_data)
        print(f"Kayıt response: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Kayıt başarılı, Token alındı: {data.get('token', 'N/A')[:20]}...")
            
            # 2. Login testi
            login_data = {
                "phone_number": "5551234567",
                "password": "SecurePass123!"
            }
            
            print("\n🔑 Login testi...")
            login_response = self.session.post(f"{self.base_url}/api/login/", json=login_data)
            print(f"Login response: {login_response.status_code}")
            
            if login_response.status_code == 200:
                login_data = login_response.json()
                access_token = login_data.get('tokens', {}).get('access')
                print(f"✅ Login başarılı, JWT Token: {access_token[:50]}..." if access_token else "❌ Token alınamadı")
                
                # 3. Korumalı endpoint'e erişim
                if access_token:
                    headers = {"Authorization": f"Bearer {access_token}"}
                    user_info_response = self.session.get(f"{self.base_url}/api/user-info/", headers=headers)
                    print(f"User info response: {user_info_response.status_code}")
                    
                    if user_info_response.status_code == 200:
                        user_info = user_info_response.json()
                        print(f"✅ Kullanıcı bilgileri alındı: {user_info.get('email')}")
                    else:
                        print("❌ Kullanıcı bilgileri alınamadı")
            else:
                print(f"❌ Login başarısız: {login_response.text}")
        else:
            print(f"❌ Kayıt başarısız: {response.text}")
    
    def test_advanced_sql_injection(self):
        """Gelişmiş SQL Injection testleri"""
        print("\n💉 Gelişmiş SQL Injection Testleri...")
        
        # Time-based blind SQL injection payloads
        time_based_payloads = [
            "1' AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT(0x7e,0x5858,0x7e) FROM information_schema.tables GROUP BY CONCAT(0x7e,0x5858,0x7e))x)--",
            "1'; WAITFOR DELAY '00:00:05'--",
            "1' OR SLEEP(5)--",
            "1' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--"
        ]
        
        for payload in time_based_payloads:
            print(f"🧪 Test payload: {payload[:50]}...")
            
            data = {
                "phone_number": payload,
                "password": "test123"
            }
            
            import time
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/api/login/", json=data)
            end_time = time.time()
            
            response_time = end_time - start_time
            print(f"   Response time: {response_time:.2f}s, Status: {response.status_code}")
            
            if response_time > 3:
                print("   🚨 Potansiyel time-based SQL injection!")
            else:
                print("   ✅ Time-based injection koruması aktif")
    
    def test_parameter_pollution(self):
        """HTTP Parameter Pollution testi"""
        print("\n🔄 HTTP Parameter Pollution Testi...")
        
        # Aynı parametreyi birden çok kez gönder
        data = "phone_number=user1&phone_number=admin&password=test123"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        response = self.session.post(f"{self.base_url}/api/login/", data=data, headers=headers)
        print(f"Parameter pollution response: {response.status_code}")
        print(f"Response content: {response.text[:200]}")
    
    def test_headers_injection(self):
        """HTTP Header Injection testi"""
        print("\n📡 HTTP Header Injection Testi...")
        
        malicious_headers = {
            "X-Forwarded-For": "127.0.0.1, <script>alert('XSS')</script>",
            "User-Agent": "Mozilla/5.0 <script>alert('XSS')</script>",
            "X-Real-IP": "../../etc/passwd",
            "X-Originating-IP": "127.0.0.1; cat /etc/passwd",
            "Authorization": "Bearer <script>alert('XSS')</script>"
        }
        
        for header, value in malicious_headers.items():
            print(f"🧪 Test header: {header}")
            
            headers = {header: value}
            response = self.session.get(f"{self.base_url}/api/user-info/", headers=headers)
            
            if value in response.text:
                print(f"   🚨 Header injection possible: {header}")
            else:
                print(f"   ✅ Header güvenli: {header}")
    
    def test_race_condition(self):
        """Race Condition testi"""
        print("\n🏃 Race Condition Testi...")
        
        import threading
        import time
        
        results = []
        
        def register_user(thread_id):
            user_data = {
                "name_surname": f"Race User {thread_id}",
                "phone_number": "5551111111",  # Aynı telefon numarası
                "email": f"race{thread_id}@test.com",
                "password": "Test123!",
                "confirm_password": "Test123!"
            }
            
            response = self.session.post(f"{self.base_url}/api/register/", json=user_data)
            results.append({
                'thread': thread_id,
                'status': response.status_code,
                'success': response.status_code == 201
            })
        
        # 5 thread aynı anda aynı telefon numarasıyla kayıt olmaya çalışsın
        threads = []
        for i in range(5):
            thread = threading.Thread(target=register_user, args=(i,))
            threads.append(thread)
        
        # Tüm thread'leri aynı anda başlat
        for thread in threads:
            thread.start()
        
        # Tüm thread'lerin bitmesini bekle
        for thread in threads:
            thread.join()
        
        successful_registrations = sum(1 for r in results if r['success'])
        print(f"Başarılı kayıt sayısı: {successful_registrations}")
        
        if successful_registrations > 1:
            print("🚨 Race condition açığı! Aynı telefon numarasıyla birden fazla kayıt")
        else:
            print("✅ Race condition koruması aktif")
    
    def test_business_logic_flaws(self):
        """İş mantığı açıklarını test et"""
        print("\n🧠 İş Mantığı Açığı Testleri...")
        
        # Negatif değerler testi
        user_data = {
            "name_surname": "Logic Test",
            "phone_number": "5552222222",
            "email": "logic@test.com",
            "password": "Test123!",
            "confirm_password": "Test123!"
        }
        
        response = self.session.post(f"{self.base_url}/api/register/", json=user_data)
        if response.status_code == 201:
            token = response.json().get('token')
            
            # Yangın ihbarı ile negatif koordinatlar
            fire_data = {
                "photo_url": "http://example.com/fire.jpg",
                "latitude": -999999.999999,
                "longitude": -999999.999999
            }
            
            headers = {"Authorization": f"Bearer {token}"}
            fire_response = self.session.post(f"{self.base_url}/api/create-fire-report/", 
                                            json=fire_data, headers=headers)
            
            print(f"Negatif koordinat testi: {fire_response.status_code}")
            if fire_response.status_code == 201:
                print("🚨 İş mantığı açığı: Negatif koordinatlar kabul edildi")
            else:
                print("✅ Koordinat validasyonu çalışıyor")
    
    def run_advanced_tests(self):
        """Tüm gelişmiş testleri çalıştır"""
        print("🎯 GELİŞMİŞ GÜVENLİK TESTLERİ")
        print("=" * 50)
        
        self.test_direct_database_access()
        self.test_authentication_flow()
        self.test_advanced_sql_injection()
        self.test_parameter_pollution()
        self.test_headers_injection()
        self.test_race_condition()
        self.test_business_logic_flaws()
        
        print("\n" + "=" * 50)
        print("✅ Gelişmiş güvenlik testleri tamamlandı")

if __name__ == "__main__":
    tester = AdvancedSecurityTester()
    tester.run_advanced_tests()
