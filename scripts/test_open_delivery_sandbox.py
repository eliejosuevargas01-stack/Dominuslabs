#!/usr/bin/env python3
"""
Script Python de validação local para integração Open Delivery.

Este script testa todos os endpoints implementados contra um servidor DominusLabs local.
Não usa APIs externas reais - apenas valida a conectividade e formato de respostas.

Variáveis de ambiente necessárias:
- DOMINUS_BASE_URL: URL base do servidor DominusLabs (ex: http://localhost:8000)
- DOMINUS_TOKEN: JWT token válido de um operador (para endpoints autenticados)
- TEST_MERCHANT_ID: ID de merchant para testes (ex: test_merchant_123)

Usage:
    export DOMINUS_BASE_URL=http://localhost:8000
    export DOMINUS_TOKEN=seu_jwt_token_aqui
    export TEST_MERCHANT_ID=test_merchant_123
    python3 scripts/test_open_delivery_sandbox.py
"""

import os
import sys
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime


class OpenDeliveryTester:
    def __init__(self):
        self.base_url = os.getenv('DOMINUS_BASE_URL', 'http://localhost:8000')
        self.auth_token = os.getenv('DOMINUS_TOKEN')
        self.test_merchant_id = os.getenv('TEST_MERCHANT_ID', 'test_merchant_123')
        
        if not self.auth_token:
            print("ERRO: Variável de ambiente DOMINUS_TOKEN não definida")
            sys.exit(1)
            
        self.headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json'
        }
        
        self.results = []
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Registra o resultado de um teste."""
        status = "PASS" if passed else "FAIL"
        self.results.append({
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        print(f"[{status}] {test_name}")
        if details:
            print(f"    {details}")
    
    def test_health_endpoint(self) -> bool:
        """Testa se o servidor está respondendo."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            if not passed:
                details += f", Response: {response.text[:200]}"
            self.log_result("Health Check", passed, details)
            return passed
        except Exception as e:
            self.log_result("Health Check", False, f"Erro de conexão: {str(e)}")
            return False
    
    def test_integrations_list(self) -> bool:
        """Testa o endpoint de listagem de integrações."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/integrations",
                headers=self.headers,
                timeout=10
            )
            passed = response.status_code == 200
            details = f"Status: {response.status_code}"
            if passed:
                try:
                    data = response.json()
                    details += f", Count: {len(data) if isinstance(data, list) else 'N/A'}"
                except:
                    details += f", Response length: {len(response.text)}"
            else:
                details += f", Response: {response.text[:200]}"
            self.log_result("List Integrations", passed, details)
            return passed
        except Exception as e:
            self.log_result("List Integrations", False, f"Erro: {str(e)}")
            return False
    
    def test_merchant_endpoint(self) -> bool:
        """Testa o endpoint GET /merchant."""
        try:
            # Primeiro testa sem X-Merchant-Id (deve falhar)
            response = requests.get(
                f"{self.base_url}/api/v1/od/pedidos10/merchant",
                headers=self.headers,
                timeout=10
            )
            
            # Deve retornar 400 pois falta o header X-Merchant-Id
            passed = response.status_code == 400
            details = f"Status (sem X-Merchant-Id): {response.status_code} (esperado 400)"
            
            # Agora testa com o header correto
            test_headers = self.headers.copy()
            test_headers['X-Merchant-Id'] = self.test_merchant_id
            
            response2 = requests.get(
                f"{self.base_url}/api/v1/od/pedidos10/merchant",
                headers=test_headers,
                timeout=10
            )
            
            # Pode retornar 404 (integração não existe) ou 200 (se existir)
            passed = passed and response2.status_code in [200, 404]
            details += f"; Status (com X-Merchant-Id): {response2.status_code}"
            
            if response2.status_code == 200:
                try:
                    data = response2.json()
                    # Verifica se tem os campos básicos do schema merchant
                    required_fields = ['id', 'name', 'document', 'address', 'categories', 'items']
                    missing_fields = [f for f in required_fields if f not in data]
                    if not missing_fields:
                        details += "; Schema merchant válido"
                    else:
                        details += f"; Campos faltando: {missing_fields}"
                except json.JSONDecodeError:
                    details += "; Resposta não é JSON válido"
            
            self.log_result("GET /merchant endpoint", passed, details)
            return passed
        except Exception as e:
            self.log_result("GET /merchant endpoint", False, f"Erro: {str(e)}")
            return False
    
    def test_order_update_endpoint(self) -> bool:
        """Testa o endpoint POST /orderUpdate com payload de exemplo."""
        try:
            # Payload mínimo para teste
            payload = {
                "merchantId": self.test_merchant_id,
                "order": {
                    "id": f"TEST-{int(datetime.now().timestamp())}",
                    "type": "DELIVERY",
                    "customer": {
                        "name": "Cliente Teste"
                    },
                    "delivery": {
                        "deliveryAddress": {
                            "street": "Rua Teste",
                            "number": "123",
                            "neighborhood": "Centro",
                            "city": "São Paulo",
                            "state": "SP",
                            "postalCode": "01234-000"
                        }
                    },
                    "total": {
                        "orderAmount": 25.50
                    },
                    "items": [
                        {
                            "externalCode": "TEST_ITEM_001",
                            "name": "Item de Teste",
                            "quantity": 1,
                            "unitPrice": 25.50,
                            "totalPrice": 25.50
                        }
                    ]
                }
            }
            
            # Testa sem token de autorização (deve falhar 401)
            no_auth_headers = {'Content-Type': 'application/json'}
            response_no_auth = requests.post(
                f"{self.base_url}/api/v1/od/pedidos10/orderUpdate",
                headers=no_auth_headers,
                json=payload,
                timeout=10
            )
            
            # Testa com token de autorização (deve falhar 401/404 pois token fake)
            response_with_auth = requests.post(
                f"{self.base_url}/api/v1/od/pedidos10/orderUpdate",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            # O primeiro deve falhar com 401 (sem auth)
            # O segundo pode falhar com 401 (token inválido) ou 404 (merchant não encontrado)
            passed = (response_no_auth.status_code == 401 and 
                     response_with_auth.status_code in [401, 404])
            
            details = f"Sem auth: {response_no_auth.status_code}; Com auth: {response_with_auth.status_code}"
            
            if response_with_auth.status_code not in [401, 404]:
                try:
                    error_data = response_with_auth.json()
                    details += f"; Response: {error_data}"
                except:
                    details += f"; Response: {response_with_auth.text[:200]}"
            
            self.log_result("POST /orderUpdate endpoint", passed, details)
            return passed
        except Exception as e:
            self.log_result("POST /orderUpdate endpoint", False, f"Erro: {str(e)}")
            return False
    
    def test_acknowledgment_endpoint(self) -> bool:
        """Testa o endpoint POST /acknowledgment."""
        try:
            payload = {
                "merchantId": self.test_merchant_id,
                "order": {
                    "id": f"TEST-ACK-{int(datetime.now().timestamp())}"
                }
            }
            
            # Testa sem token de autorização (deve falhar 401)
            no_auth_headers = {'Content-Type': 'application/json'}
            response_no_auth = requests.post(
                f"{self.base_url}/api/v1/od/pedidos10/events/acknowledgment",
                headers=no_auth_headers,
                json=payload,
                timeout=10
            )
            
            # Testa com token de autorização
            response_with_auth = requests.post(
                f"{self.base_url}/api/v1/od/pedidos10/events/acknowledgment",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            # Primeiro deve ser 401, segundo pode ser 200, 401 ou 404
            passed = (response_no_auth.status_code == 401 and 
                     response_with_auth.status_code in [200, 401, 404])
            
            details = f"Sem auth: {response_no_auth.status_code}; Com auth: {response_with_auth.status_code}"
            
            self.log_result("POST /acknowledgment endpoint", passed, details)
            return passed
        except Exception as e:
            self.log_result("POST /acknowledgment endpoint", False, f"Erro: {str(e)}")
            return False
    
    def run_all_tests(self) -> bool:
        """Executa todos os testes e retorna se todos passaram."""
        print("Iniciando testes de validação Open Delivery...")
        print(f"Base URL: {self.base_url}")
        print(f"Test Merchant ID: {self.test_merchant_id}")
        print("-" * 50)
        
        # Testa se o servidor está online primeiro
        if not self.test_health_endpoint():
            print("\nServidor não está respondendo. Verifique se o DominusLabs está rodando.")
            return False
        
        # Executa os testes
        self.test_integrations_list()
        self.test_merchant_endpoint()
        self.test_order_update_endpoint()
        self.test_acknowledgment_endpoint()
        
        print("-" * 50)
        print("RESUMO DOS TESTES:")
        
        passed_count = sum(1 for r in self.results if r['status'] == 'PASS')
        total_count = len(self.results)
        
        for result in self.results:
            print(f"[{result['status']}] {result['test']}")
        
        print(f"\nTotal: {passed_count}/{total_count} testes passaram")
        
        all_passed = passed_count == total_count
        if all_passed:
            print("✅ Todos os testes passaram!")
        else:
            print("❌ Alguns testes falharam. Verifique os detalhes acima.")
        
        return all_passed


def main():
    """Função principal."""
    tester = OpenDeliveryTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()