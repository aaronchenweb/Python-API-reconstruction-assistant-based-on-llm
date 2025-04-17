"""
身份驗證重構助手 - 提供 API 身份驗證機制的分析和改進工具
"""
import ast
import os
import re
from typing import Dict, List, Tuple, Optional, Any

from utils.file_operations import read_file, write_file
from api_analyzer.auth_analyzer import AuthAnalyzer
from code_analyzer.ast_parser import analyze_python_file


class AuthRefactoringHelper:
    """提供 API 身份驗證機制的分析和改進工具"""
    
    def __init__(self, project_path: str, framework: Optional[str] = None):
        """
        初始化身份驗證重構助手
        
        Args:
            project_path: API 專案的路徑
            framework: 專案使用的框架（如果已知）
        """
        self.project_path = project_path
        self.framework = framework
        self.auth_analyzer = AuthAnalyzer(project_path, framework)
        
    def analyze_auth_security(self) -> Dict[str, Any]:
        """
        分析身份驗證機制的安全性
        
        Returns:
            身份驗證安全性分析結果
        """
        # 獲取身份驗證方法和問題
        auth_methods = self.auth_analyzer.analyze_auth_methods()
        security_issues = self.auth_analyzer.identify_security_issues()
        
        # 分析安全性
        security_analysis = {
            'auth_methods': auth_methods,
            'security_issues': security_issues,
            'security_score': self._calculate_security_score(auth_methods, security_issues),
            'improvement_suggestions': self._generate_auth_improvement_suggestions(auth_methods, security_issues)
        }
        
        return security_analysis
    
    def _calculate_security_score(
        self, auth_methods: List[Dict[str, Any]], security_issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        計算身份驗證安全性分數
        
        Args:
            auth_methods: 身份驗證方法列表
            security_issues: 安全問題列表
            
        Returns:
            安全性分數資訊
        """
        # 基本分數，滿分 100
        base_score = 70
        
        # 根據身份驗證方法評分
        method_scores = {
            'django_rest_framework': 15,  # DRF 有良好的安全實踐
            'flask_jwt': 15,             # JWT 提供強大的保護
            'flask_login': 10,           # 基本但功能完整
            'fastapi_security': 15,      # FastAPI 安全功能良好
            'django_decorator': 10,      # 基本保護
            'potential_auth_function': 0  # 不確定的自定義方法
        }
        
        # 添加使用的方法分數
        for method in auth_methods:
            method_type = method.get('type', '')
            if method_type in method_scores:
                base_score += method_scores[method_type] / len(auth_methods)  # 平均分數
                
                # 對於不確定的自定義方法，降低分數
                if method_type == 'potential_auth_function' and method.get('confidence') == 'low':
                    base_score -= 5
        
        # 根據安全問題扣分
        severity_penalties = {
            'high': 15,
            'medium': 10,
            'low': 5
        }
        
        for issue in security_issues:
            severity = issue.get('severity', 'low')
            base_score -= severity_penalties.get(severity, 5)
        
        # 確保分數在 0-100 範圍內
        final_score = max(0, min(100, base_score))
        
        # 根據分數評定等級
        rating = 'F'
        if final_score >= 90:
            rating = 'A'
        elif final_score >= 80:
            rating = 'B'
        elif final_score >= 70:
            rating = 'C'
        elif final_score >= 60:
            rating = 'D'
        
        return {
            'score': final_score,
            'rating': rating,
            'factors': {
                'auth_methods': [method.get('type', '') for method in auth_methods],
                'security_issues_count': len(security_issues)
            }
        }
    
    def _generate_auth_improvement_suggestions(
        self, auth_methods: List[Dict[str, Any]], security_issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        生成身份驗證改進建議
        
        Args:
            auth_methods: 身份驗證方法列表
            security_issues: 安全問題列表
            
        Returns:
            改進建議列表
        """
        suggestions = []
        
        # 如果沒有身份驗證方法，建議實施
        if not auth_methods:
            if self.framework == 'django':
                suggestions.append({
                    'title': '實施 Django REST Framework 身份驗證',
                    'description': '您的 API 缺少身份驗證系統。建議使用 Django REST Framework 的身份驗證機制。',
                    'priority': 'high',
                    'implementation_guide': self._get_django_auth_guide()
                })
            elif self.framework == 'flask':
                suggestions.append({
                    'title': '實施 Flask JWT 身份驗證',
                    'description': '您的 API 缺少身份驗證系統。建議使用 Flask-JWT-Extended 或類似庫實施 JWT 身份驗證。',
                    'priority': 'high',
                    'implementation_guide': self._get_flask_auth_guide()
                })
            elif self.framework == 'fastapi':
                suggestions.append({
                    'title': '實施 FastAPI 安全依賴',
                    'description': '您的 API 缺少身份驗證系統。建議使用 FastAPI 的安全依賴實施身份驗證。',
                    'priority': 'high',
                    'implementation_guide': self._get_fastapi_auth_guide()
                })
            else:
                suggestions.append({
                    'title': '實施 API 身份驗證',
                    'description': '您的 API 缺少身份驗證系統。建議實施強大的身份驗證機制，如基於令牌的身份驗證或 OAuth2。',
                    'priority': 'high',
                    'implementation_guide': self._get_generic_auth_guide()
                })
        
        # 根據安全問題提出建議
        for issue in security_issues:
            issue_type = issue.get('type', '')
            
            if issue_type == 'hardcoded_secret':
                suggestions.append({
                    'title': '移除硬編碼機密',
                    'description': '在代碼中檢測到硬編碼機密（密碼、API 金鑰等），這是一個重要的安全風險。',
                    'priority': 'high',
                    'implementation_guide': {
                        'steps': [
                            '使用環境變數存儲機密',
                            '考慮使用專用的機密管理解決方案',
                            '確保機密不會被檢入版本控制系統'
                        ],
                        'code_example': '''
# 不好的做法
API_KEY = "1234567890abcdef"

# 好的做法
import os
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise EnvironmentError("API_KEY 環境變數未設定")
'''
                    }
                })
            
            elif issue_type == 'missing_auth':
                suggestions.append({
                    'title': '為所有端點添加身份驗證',
                    'description': '某些端點缺少身份驗證保護，這可能允許未經授權的訪問。',
                    'priority': 'high',
                    'implementation_guide': {
                        'steps': [
                            '識別所有缺少身份驗證的端點',
                            '實施適當的身份驗證檢查',
                            '對公共端點進行明確的文檔說明'
                        ],
                        'framework_specific': self._get_framework_auth_example(self.framework)
                    }
                })
            
            elif issue_type == 'insecure_setting':
                suggestions.append({
                    'title': '修復不安全的配置',
                    'description': f"檢測到不安全的配置設置: {issue.get('setting', '')}。",
                    'priority': 'medium',
                    'implementation_guide': {
                        'steps': [
                            '審核所有安全相關的配置',
                            '遵循框架的安全最佳實踐',
                            '在生產環境中禁用調試模式'
                        ]
                    }
                })
        
        # 添加通用建議
        method_types = [method.get('type', '') for method in auth_methods]
        
        # 如果使用基本身份驗證，建議升級到更安全的方法
        if 'basic_auth' in method_types:
            suggestions.append({
                'title': '從基本身份驗證升級到令牌身份驗證',
                'description': '基本身份驗證不夠安全，特別是對於公共 API。建議使用令牌或 OAuth2 等更強大的方法。',
                'priority': 'medium',
                'implementation_guide': self._get_token_auth_guide()
            })
        
        # 如果使用自定義身份驗證，建議使用標準方法
        if any('potential' in t for t in method_types):
            suggestions.append({
                'title': '用標準身份驗證方法替換自定義方法',
                'description': '自定義身份驗證方法可能缺少關鍵安全特性，並難以維護。考慮使用框架提供的標準方法。',
                'priority': 'medium',
                'implementation_guide': self._get_framework_auth_guide()
            })
        
        # 如果沒有 HTTPS，建議實施
        suggestions.append({
            'title': '確保所有 API 通訊使用 HTTPS',
            'description': 'API 應始終通過 HTTPS 提供，以確保通訊加密。',
            'priority': 'high',
            'implementation_guide': {
                'steps': [
                    '獲取有效的 SSL/TLS 證書',
                    '配置您的 Web 服務器以強制執行 HTTPS',
                    '實施 HTTP 嚴格傳輸安全 (HSTS)'
                ]
            }
        })
        
        # 如果沒有速率限制，建議實施
        suggestions.append({
            'title': '實施 API 速率限制',
            'description': '速率限制可以防止暴力攻擊和服務拒絕攻擊。',
            'priority': 'medium',
            'implementation_guide': self._get_rate_limiting_guide()
        })
        
        return suggestions
    
    def _get_django_auth_guide(self) -> Dict[str, Any]:
        """
        獲取 Django 身份驗證實施指南
        
        Returns:
            實施指南
        """
        return {
            'steps': [
                '安裝 djangorestframework',
                '設置身份驗證類',
                '創建權限類',
                '將身份驗證應用於視圖或視圖集'
            ],
            'code_example': '''
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}

# views.py
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

class UserViewSet(ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    # ...

# urls.py
from django.urls import path
from rest_framework.authtoken import views as token_views

urlpatterns = [
    # ...
    path('api-token-auth/', token_views.obtain_auth_token),
]
'''
        }
    
    def _get_flask_auth_guide(self) -> Dict[str, Any]:
        """
        獲取 Flask 身份驗證實施指南
        
        Returns:
            實施指南
        """
        return {
            'steps': [
                '安裝 Flask-JWT-Extended',
                '配置 JWT 設置',
                '創建令牌生成和驗證函數',
                '保護路由'
            ],
            'code_example': '''
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity

app = Flask(__name__)

# 配置
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')  # 使用環境變數!
jwt = JWTManager(app)

# 登入端點
@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    
    # 檢查憑證 (使用正確的密碼驗證!)
    if username != 'test' or password != 'test':
        return jsonify({"error": "帳號或密碼錯誤"}), 401
    
    # 創建 JWT 令牌
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)

# 受保護的端點
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200
'''
        }
    
    def _get_fastapi_auth_guide(self) -> Dict[str, Any]:
        """
        獲取 FastAPI 身份驗證實施指南
        
        Returns:
            實施指南
        """
        return {
            'steps': [
                '定義安全方案',
                '創建令牌生成函數',
                '實現令牌驗證依賴',
                '應用依賴於端點'
            ],
            'code_example': '''
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

# 安全配置
SECRET_KEY = os.environ.get("SECRET_KEY")  # 使用環境變數!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 創建令牌
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 令牌驗證依賴
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無效憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 這裡應該有獲取並驗證用戶的代碼
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user

# 令牌端點
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # 驗證用戶（這是示例代碼，您應該使用正確的驗證）
    if form_data.username != "test" or form_data.password != "test":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# 受保護的端點
@app.get("/users/me")
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user
'''
        }
    
    def _get_generic_auth_guide(self) -> Dict[str, Any]:
        """
        獲取通用身份驗證實施指南
        
        Returns:
            實施指南
        """
        return {
            'steps': [
                '選擇適當的身份驗證方案（JWT、OAuth2 等）',
                '安裝和配置身份驗證庫',
                '設置用戶驗證和管理',
                '保護 API 端點'
            ],
            'auth_options': [
                {
                    'name': 'JWT (JSON Web Tokens)',
                    'description': '無狀態令牌身份驗證，易於實現且適用於分佈式系統',
                    'use_cases': 'RESTful API、SPA、移動應用等',
                    'pros': [
                        '無狀態，不需要服務器端會話',
                        '可以包含聲明（claims）',
                        '易於實現跨服務身份驗證'
                    ],
                    'cons': [
                        '令牌吊銷較複雜',
                        '令牌大小限制',
                        '安全性依賴於正確配置'
                    ]
                },
                {
                    'name': 'OAuth2',
                    'description': '授權框架，允許第三方應用訪問資源',
                    'use_cases': '需要第三方授權的 API、複雜的身份驗證需求',
                    'pros': [
                        '強大且靈活',
                        '支持不同的授權流程',
                        '成熟且廣泛採用的標準'
                    ],
                    'cons': [
                        '實現複雜',
                        '配置和維護更加困難',
                        '可能過於複雜，對於簡單的 API 是大材小用'
                    ]
                },
                {
                    'name': 'API 金鑰',
                    'description': '簡單的密鑰身份驗證',
                    'use_cases': '內部 API、合作夥伴 API',
                    'pros': [
                        '實現簡單',
                        '容易理解',
                        '適合服務間通訊'
                    ],
                    'cons': [
                        '安全性較低',
                        '不支持細粒度權限',
                        '密鑰共享和管理可能困難'
                    ]
                }
            ]
        }
    
    def _get_framework_auth_guide(self) -> Dict[str, Any]:
        """
        根據框架獲取身份驗證實施指南
        
        Returns:
            實施指南
        """
        if self.framework == 'django':
            return self._get_django_auth_guide()
        elif self.framework == 'flask':
            return self._get_flask_auth_guide()
        elif self.framework == 'fastapi':
            return self._get_fastapi_auth_guide()
        else:
            return self._get_generic_auth_guide()
    
    def _get_framework_auth_example(self, framework: str) -> Dict[str, str]:
        """
        獲取特定框架的身份驗證代碼示例
        
        Args:
            framework: 框架名稱
            
        Returns:
            代碼示例字典
        """
        examples = {}
        
        if framework == 'django':
            examples['decorator'] = '''
# views.py
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def protected_view(request):
    return Response({"message": "This is a protected endpoint"})
'''
            
            examples['class_view'] = '''
# views.py
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class ProtectedView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({"message": "This is a protected endpoint"})
'''
        
        elif framework == 'flask':
            examples['decorator'] = '''
# app.py
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # 使用環境變數!
jwt = JWTManager(app)

@app.route('/api/protected')
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user)
'''
            
            examples['blueprint'] = '''
# auth.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/profile')
@jwt_required()
def profile():
    current_user = get_jwt_identity()
    return jsonify(user=current_user)
'''
        
        elif framework == 'fastapi':
            examples['dependency'] = '''
# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    # 實際應用中，這裡應該解碼和驗證令牌
    if token != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": "test_user"}

@app.get("/users/me")
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user
'''
            
            examples['router'] = '''
# users.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    if token != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": "test_user"}

@router.get("/users/me")
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user
'''
        
        return examples
    
    def _get_token_auth_guide(self) -> Dict[str, Any]:
        """
        獲取令牌身份驗證指南
        
        Returns:
            令牌身份驗證指南
        """
        return {
            'title': '從基本身份驗證遷移到令牌身份驗證',
            'steps': [
                '設置令牌生成和驗證',
                '創建令牌發放端點',
                '在受保護的端點上使用令牌驗證',
                '實施令牌吊銷（可選但推薦）'
            ],
            'code_example': '''
# 假設的偽代碼示例

# 1. 初始化身份驗證系統
auth_system = TokenAuthSystem(secret_key=os.environ.get("SECRET_KEY"))

# 2. 令牌發放端點
@app.route("/api/token", methods=["POST"])
def get_token():
    username = request.json.get("username")
    password = request.json.get("password")
    
    if verify_credentials(username, password):
        token = auth_system.generate_token(user_id=get_user_id(username))
        return {"token": token}
    else:
        return {"error": "Invalid credentials"}, 401

# 3. 受保護的端點
@app.route("/api/protected-resource")
@auth_system.require_token
def protected_resource():
    user_id = auth_system.get_current_user_id()
    return {"data": "This is protected", "user_id": user_id}
'''
        }
    
    def _get_rate_limiting_guide(self) -> Dict[str, Any]:
        """
        獲取速率限制實施指南
        
        Returns:
            速率限制指南
        """
        guide = {
            'title': '實施 API 速率限制',
            'description': '速率限制可以防止 API 被濫用，並保護您的服務器免受過度負載。',
            'steps': [
                '選擇速率限制策略（每 IP、每用戶、每 API 密鑰等）',
                '設置適當的限制閾值',
                '實施限制計數器和存儲',
                '添加適當的限制標頭',
                '配置超過限制時的行為'
            ]
        }
        
        if self.framework == 'django':
            guide['code_example'] = '''
# 使用 Django REST Framework 實施速率限制

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    }
}

# views.py
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

class CustomUserRateThrottle(UserRateThrottle):
    rate = '5/minute'

class APIView(views.APIView):
    throttle_classes = [AnonRateThrottle, CustomUserRateThrottle]
    # ...
'''
        elif self.framework == 'flask':
            guide['code_example'] = '''
# 使用 Flask-Limiter 實施速率限制

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route("/api/limited-endpoint")
@limiter.limit("5 per minute")
def limited_endpoint():
    return {"data": "This is rate limited"}
'''
        elif self.framework == 'fastapi':
            guide['code_example'] = '''
# 使用 FastAPI 內置的限制依賴實施速率限制

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/limited-endpoint")
@limiter.limit("5/minute")
async def limited_endpoint():
    return {"data": "This is rate limited"}
'''
        
        return guide
    
    def generate_auth_upgrade_plan(self, target_auth_method: str) -> Dict[str, Any]:
        """
        生成身份驗證升級計劃
        
        Args:
            target_auth_method: 目標身份驗證方法
            
        Returns:
            身份驗證升級計劃
        """
        # 分析當前身份驗證狀態
        auth_methods = self.auth_analyzer.analyze_auth_methods()
        current_auth_method = auth_methods[0].get('type', 'none') if auth_methods else 'none'
        
        # 初始化升級計劃
        upgrade_plan = {
            'current_auth_method': current_auth_method,
            'target_auth_method': target_auth_method,
            'phases': [],
            'code_examples': {}
        }
        
        # 根據當前和目標方法生成升級計劃
        if current_auth_method == 'none':
            # 從無身份驗證升級
            upgrade_plan['phases'] = self._generate_new_auth_phases(target_auth_method)
        else:
            # 從一種方法升級到另一種
            upgrade_plan['phases'] = self._generate_auth_migration_phases(current_auth_method, target_auth_method)
        
        # 添加目標身份驗證方法的代碼示例
        upgrade_plan['code_examples'] = self._get_auth_method_examples(target_auth_method)
        
        return upgrade_plan
    
    def _generate_new_auth_phases(self, target_auth_method: str) -> List[Dict[str, Any]]:
        """
        生成新身份驗證實施階段
        
        Args:
            target_auth_method: 目標身份驗證方法
            
        Returns:
            實施階段列表
        """
        phases = [
            {
                'name': '準備工作',
                'description': '設置必要的依賴項和配置',
                'tasks': [
                    f'安裝 {target_auth_method} 相關庫',
                    '更新配置以啟用身份驗證',
                    '設計用戶模型和身份驗證流程',
                    '配置安全相關的設置'
                ]
            },
            {
                'name': '實施核心身份驗證',
                'description': '建立基本身份驗證框架',
                'tasks': [
                    '創建用戶創建和管理功能',
                    '實施登入功能',
                    '設置令牌生成和驗證',
                    '實施基本的權限系統'
                ]
            },
            {
                'name': '保護 API 端點',
                'description': '應用身份驗證於 API 端點',
                'tasks': [
                    '識別需要保護的端點',
                    '應用身份驗證中間件或裝飾器',
                    '添加權限檢查',
                    '測試端點的安全性'
                ]
            },
            {
                'name': '增強功能和安全性',
                'description': '添加進階身份驗證功能',
                'tasks': [
                    '實施密碼重置功能',
                    '添加雙因素身份驗證（可選）',
                    '配置令牌到期和刷新',
                    '實施賬戶鎖定和保護措施'
                ]
            },
            {
                'name': '測試和文檔',
                'description': '全面測試並記錄身份驗證系統',
                'tasks': [
                    '創建安全相關測試套件',
                    '執行安全審計和漏洞評估',
                    '撰寫開發人員文檔',
                    '為 API 消費者準備身份驗證指南'
                ]
            }
        ]
        
        return phases
    
    def _generate_auth_migration_phases(self, current_auth_method: str, target_auth_method: str) -> List[Dict[str, Any]]:
        """
        生成身份驗證遷移階段
        
        Args:
            current_auth_method: 當前身份驗證方法
            target_auth_method: 目標身份驗證方法
            
        Returns:
            遷移階段列表
        """
        phases = [
            {
                'name': '規劃和準備',
                'description': '準備從 ' + current_auth_method + ' 遷移到 ' + target_auth_method,
                'tasks': [
                    '審核當前身份驗證實施',
                    '確定使用當前身份驗證的所有端點',
                    '設計新的身份驗證流程',
                    '規劃遷移策略'
                ]
            },
            {
                'name': '實施新身份驗證系統',
                'description': '並行建立新的身份驗證系統',
                'tasks': [
                    f'安裝和配置 {target_auth_method} 相關庫',
                    '實施新的用戶驗證和令牌管理',
                    '創建新的身份驗證端點',
                    '測試新系統的功能'
                ]
            },
            {
                'name': '雙重支援階段',
                'description': '同時支援舊系統和新系統',
                'tasks': [
                    '更新端點以接受兩種身份驗證方法',
                    '實施用戶憑證遷移機制',
                    '向客戶端通知即將發生的更改',
                    '監控兩個系統的使用情況'
                ]
            },
            {
                'name': '遷移客戶端',
                'description': '協助客戶端遷移到新系統',
                'tasks': [
                    '提供新身份驗證系統的文檔',
                    '為客戶端開發人員提供支援',
                    '提供遷移腳本或工具',
                    '設定舊系統的棄用時間表'
                ]
            },
            {
                'name': '完成遷移',
                'description': '完成遷移並停用舊系統',
                'tasks': [
                    '確認所有客戶端都已遷移',
                    '移除舊身份驗證系統',
                    '清理遺留代碼和配置',
                    '最終驗證和安全審計'
                ]
            }
        ]
        
        return phases
    
    def _get_auth_method_examples(self, auth_method: str) -> Dict[str, str]:
        """
        獲取身份驗證方法的代碼示例
        
        Args:
            auth_method: 身份驗證方法
            
        Returns:
            代碼示例字典
        """
        examples = {}
        
        if auth_method == 'jwt':
            if self.framework == 'django':
                examples['setup'] = '''
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'rest_framework_simplejwt',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
'''
                examples['usage'] = '''
# urls.py
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # ...
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({"message": "This is a protected endpoint"})
'''
            elif self.framework == 'flask':
                examples['setup'] = '''
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)
'''
                examples['usage'] = '''
@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    
    # 驗證用戶 (在實際應用中，應檢查資料庫中的憑證)
    if username != 'test' or password != 'test':
        return jsonify({"msg": "帳號或密碼錯誤"}), 401
    
    # 創建 JWT
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    # 獲取當前用戶標識
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user)
'''
            elif self.framework == 'fastapi':
                examples['setup'] = '''
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta

# 配置
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
'''
                examples['usage'] = '''
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無效憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return {"username": username}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # 驗證用戶
    if form_data.username != "test" or form_data.password != "test":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤"
        )
    
    # 創建令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user
'''
        
        elif auth_method == 'oauth2':
            if self.framework == 'django':
                examples['setup'] = '''
# settings.py
INSTALLED_APPS = [
    # ...
    'oauth2_provider',
    'rest_framework',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    ],
}

OAUTH2_PROVIDER = {
    'SCOPES': {'read': 'Read scope', 'write': 'Write scope'}
}
'''
                examples['usage'] = '''
# urls.py
from django.urls import path, include

urlpatterns = [
    # ...
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]

# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from oauth2_provider.contrib.rest_framework import TokenHasReadScope, TokenHasWriteScope

class ProtectedReadView(APIView):
    permission_classes = [IsAuthenticated, TokenHasReadScope]
    
    def get(self, request):
        return Response({"message": "This is a protected read endpoint"})

class ProtectedWriteView(APIView):
    permission_classes = [IsAuthenticated, TokenHasWriteScope]
    
    def post(self, request):
        return Response({"message": "This is a protected write endpoint"})
'''
            elif self.framework == 'flask':
                examples['setup'] = '''
from flask import Flask
from authlib.integrations.flask_oauth2 import AuthorizationServer, ResourceProtector
from authlib.integrations.sqla_oauth2 import create_bearer_token_validator

app = Flask(__name__)
app.config.update({
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///oauth2.db',
    'OAUTH2_ACCESS_TOKEN_GENERATOR': 'app.generators.generate_access_token',
})

# 設置 OAuth2 服務器
server = AuthorizationServer(app, generate_token=generate_token)
require_oauth = ResourceProtector()
bearer_cls = create_bearer_token_validator(db.session, OAuth2TokenMixin)
require_oauth.register_token_validator(bearer_cls())
'''
                examples['usage'] = '''
# 注冊端點
@app.route('/oauth/token', methods=['POST'])
def issue_token():
    return server.create_token_response()

@app.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    if request.method == 'GET':
        # 顯示授權表單
        return render_template('authorize.html')
    
    # 確認授權
    grant = server.validate_consent_request(end_user=current_user)
    return server.create_authorization_response(grant_user=current_user)

# 受保護的資源
@app.route('/api/me')
@require_oauth('profile')
def api_me():
    user = current_token.user
    return jsonify(id=user.id, username=user.username)
'''
            elif self.framework == 'fastapi':
                examples['setup'] = '''
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta

app = FastAPI()

# OAuth2 設置
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
'''
                examples['usage'] = '''
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # 驗證用戶
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 創建令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": form_data.scopes},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# 帶作用域的端點
@app.get("/users/me")
async def read_users_me(current_user = Depends(get_current_user_with_scopes(['read:profile']))):
    return current_user
'''
        
        elif auth_method == 'api_key':
            if self.framework == 'django':
                examples['setup'] = '''
# authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import APIKey

class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None
        
        try:
            key = APIKey.objects.get(key=api_key, is_active=True)
            return (key.user, None)
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('無效的 API 金鑰')
'''
                examples['usage'] = '''
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'path.to.authentication.APIKeyAuthentication',
    ],
}

# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({"message": "This is a protected endpoint"})
'''
            elif self.framework == 'flask':
                examples['setup'] = '''
from flask import Flask, jsonify, request
from functools import wraps

app = Flask(__name__)

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "API 金鑰缺失"}), 401
        
        # 在實際應用中，應檢查資料庫中的金鑰
        if api_key != "valid_api_key":
            return jsonify({"error": "無效的 API 金鑰"}), 401
        
        return f(*args, **kwargs)
    return decorated
'''
                examples['usage'] = '''
@app.route('/api/protected')
@require_api_key
def protected():
    return jsonify({"message": "This is a protected endpoint"})

@app.route('/api/keys', methods=['POST'])
@require_api_key
def create_api_key():
    # 創建新的 API 金鑰
    new_key = generate_api_key()
    return jsonify({"api_key": new_key})
'''
            elif self.framework == 'fastapi':
                examples['setup'] = '''
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader, APIKey

app = FastAPI()

API_KEY_NAME = "X-API-Key"
API_KEY = "your-api-key"  # 在實際應用中，應存儲在安全位置

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="無效的 API 金鑰"
        )
'''
                examples['usage'] = '''
@app.get("/api/protected")
async def protected_endpoint(api_key: APIKey = Depends(get_api_key)):
    return {"message": "This is a protected endpoint"}

@app.post("/api/keys")
async def create_api_key(api_key: APIKey = Depends(get_api_key)):
    # 創建新的 API 金鑰
    new_key = generate_api_key()
    return {"api_key": new_key}
'''
        
        return examples