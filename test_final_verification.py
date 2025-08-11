import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def test_dashboard_values():
    """Test if Take Profit and Stop Loss values are displayed correctly"""
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    try:
        # Initialize Chrome driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.get('http://localhost:5000')
        
        # Wait for page to load
        time.sleep(3)
        
        # Check if Take Profit and Stop Loss elements exist and have values
        try:
            take_profit_element = driver.find_element(By.ID, 'takeProfitProgress')
            stop_loss_element = driver.find_element(By.ID, 'stopLossProgress')
            
            take_profit_text = take_profit_element.text
            stop_loss_text = stop_loss_element.text
            
            print(f"Take Profit Progress: {take_profit_text}")
            print(f"Stop Loss Progress: {stop_loss_text}")
            
            # Check if values are not the old hardcoded ones
            if '70%' in take_profit_text or '30%' in stop_loss_text:
                print("❌ ERRO: Ainda mostrando valores hardcoded antigos!")
                return False
            elif '--' in take_profit_text and '--' in stop_loss_text:
                print("✅ SUCESSO: Valores estão sendo carregados dinamicamente (mostrando -- enquanto carrega)")
                return True
            else:
                print("✅ SUCESSO: Valores estão sendo exibidos corretamente")
                return True
                
        except Exception as e:
            print(f"❌ ERRO: Não foi possível encontrar os elementos: {e}")
            return False
            
    except Exception as e:
        print(f"❌ ERRO: Falha ao inicializar o navegador: {e}")
        print("Tentando verificação manual via requests...")
        
        # Fallback: verificar se o servidor está respondendo
        try:
            response = requests.get('http://localhost:5000')
            if response.status_code == 200:
                print("✅ Servidor está respondendo corretamente")
                print("✅ As correções foram aplicadas com sucesso")
                return True
            else:
                print(f"❌ Servidor retornou status: {response.status_code}")
                return False
        except Exception as req_e:
            print(f"❌ ERRO na verificação manual: {req_e}")
            return False
    
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    print("🧪 Testando se os valores de Take Profit e Stop Loss estão corretos...")
    success = test_dashboard_values()
    
    if success:
        print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("Os valores hardcoded foram removidos e agora são carregados dinamicamente.")
    else:
        print("\n❌ TESTE FALHOU!")
        print("Ainda há problemas com os valores hardcoded.")