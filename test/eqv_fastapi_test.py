"""
FastAPI 服务测试类

本模块提供了对 ExamQuestionVerification FastAPI 服务的完整测试功能。
包含对所有端点的测试：健康检查、考题核查、考题修复、考题核查并修复。

使用方法：
    # 直接运行测试
    python fastapi_test.py
    
    # 或者在其他模块中使用
    from fastapi_test import FastAPITester
    tester = FastAPITester()
    await tester.test_all_endpoints()
"""

import asyncio
import json
from typing import Dict, Any, Optional
import httpx
import yaml
import os
from datetime import datetime

BASE_URL = "http://192.168.2.13:8022"

class FastAPITester:
    """FastAPI 服务测试类"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """
        初始化测试器
        
        Args:
            base_url: API服务的基础URL，如果不提供则从配置文件读取
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        
        if base_url:
            self.base_url = base_url
        else:
            # 读取服务地址
            self.base_url = BASE_URL
        
        # 测试数据
        self.test_data = self._prepare_test_data()
        
        # 测试结果记录
        self.test_results = []
    
    def _prepare_test_data(self) -> Dict[str, Any]:
        """准备测试数据"""
        return {
            "valid_exam_question": {
                "question": "请简述BFS和DFS搜索算法的区别",
                "answer": "BFS按层扩展，使用队列；DFS深度优先，使用栈或递归",
                "question_type": "简答题",
                "knowledge_point": "图搜索算法",
                "knowledge_point_description": "DFS/BFS基础与最短路径问题",
                "extra_requirement": "表达清晰，分点说明"
            },
            "invalid_exam_question": {
                "question": "题目",  # 太短
                "answer": "",  # 空答案
                "question_type": "unknown_type",  # 无效类型
                "knowledge_point": "",
                "knowledge_point_description": "",
                "extra_requirement": ""
            },
            "verification_result": {
                "is_compliant": False,
                "suggestion": "题干过长且不够明确，请拆分并增加约束。"
            },
            "fix_request": {
                "exam_question": {
                    "question": "请简述BFS和DFS搜索算法的区别",
                    "answer": "BFS按层扩展，使用队列；DFS深度优先，使用栈或递归",
                    "question_type": "简答题",
                    "knowledge_point": "图搜索算法",
                    "knowledge_point_description": "DFS/BFS基础与最短路径问题",
                    "extra_requirement": "表达清晰，分点说明"
                },
                "verification_result": {
                    "is_compliant": False,
                    "suggestion": "题干过长且不够明确，请拆分并增加约束。"
                }
            },
            "verify_and_fix_request": {
                "exam_question": {
                    "question": "请简述BFS和DFS搜索算法的区别",
                    "answer": "BFS按层扩展，使用队列；DFS深度优先，使用栈或递归",
                    "question_type": "简答题",
                    "knowledge_point": "图搜索算法",
                    "knowledge_point_description": "DFS/BFS基础与最短路径问题",
                    "extra_requirement": "答案需要表达清晰，分点说明"
                },
                "max_fix_attempts": 3
            }
        }
    
    def _log_test_result(self, test_name: str, success: bool, response_data: Any = None, error: str = None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data,
            "error": error
        }
        self.test_results.append(result)
        
        # 打印测试结果
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if error:
            print(f"   错误: {error}")
        if response_data and isinstance(response_data, dict):
            print(f"   响应: {response_data.get('message', 'N/A')}")
        print()
    
    async def test_root_endpoint(self) -> bool:
        """测试根路径端点 GET /"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/")
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("code") == 0
                    self._log_test_result("GET / (欢迎页)", success, data)
                    return success
                else:
                    self._log_test_result("GET / (欢迎页)", False, error=f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self._log_test_result("GET / (欢迎页)", False, error=str(e))
            return False
    
    async def test_health_endpoint(self) -> bool:
        """测试健康检查端点 GET /health"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("code") == 0 and data.get("data", {}).get("status") == "healthy"
                    self._log_test_result("GET /health (健康检查)", success, data)
                    return success
                else:
                    self._log_test_result("GET /health (健康检查)", False, error=f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self._log_test_result("GET /health (健康检查)", False, error=str(e))
            return False
    
    async def test_verify_endpoint(self) -> bool:
        """测试考题核查端点 POST /api/v1/verify"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 测试有效数据
                response = await client.post(
                    f"{self.base_url}/api/v1/verify",
                    json=self.test_data["valid_exam_question"]
                )
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("code") == 0 and "data" in data
                    self._log_test_result("POST /api/v1/verify (考题核查-有效数据)", success, data)
                    
                    # 测试无效数据
                    try:
                        response_invalid = await client.post(
                            f"{self.base_url}/api/v1/verify",
                            json=self.test_data["invalid_exam_question"]
                        )
                        # 无效数据应该返回400或422状态码
                        invalid_success = response_invalid.status_code in [400, 422]
                        self._log_test_result("POST /api/v1/verify (考题核查-无效数据)", invalid_success, 
                                            {"status_code": response_invalid.status_code})
                        
                        return success and invalid_success
                    except Exception as e:
                        self._log_test_result("POST /api/v1/verify (考题核查-无效数据)", False, error=str(e))
                        return success
                        
                else:
                    self._log_test_result("POST /api/v1/verify (考题核查-有效数据)", False, 
                                        error=f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self._log_test_result("POST /api/v1/verify (考题核查)", False, error=str(e))
            return False
    
    async def test_fix_endpoint(self) -> bool:
        """测试考题修复端点 POST /api/v1/fix"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/fix",
                    json=self.test_data["fix_request"]
                )
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("code") == 0 and "data" in data
                    self._log_test_result("POST /api/v1/fix (考题修复)", success, data)
                    return success
                else:
                    self._log_test_result("POST /api/v1/fix (考题修复)", False, 
                                        error=f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self._log_test_result("POST /api/v1/fix (考题修复)", False, error=str(e))
            return False
    
    async def test_verify_and_fix_endpoint(self) -> bool:
        """测试考题核查并修复端点 POST /api/v1/verify-and-fix"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/verify-and-fix",
                    json=self.test_data["verify_and_fix_request"]
                )
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("code") == 0 and "data" in data
                    self._log_test_result("POST /api/v1/verify-and-fix (考题核查并修复)", success, data)
                    return success
                else:
                    self._log_test_result("POST /api/v1/verify-and-fix (考题核查并修复)", False, 
                                        error=f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self._log_test_result("POST /api/v1/verify-and-fix (考题核查并修复)", False, error=str(e))
            return False
    
    async def test_all_endpoints(self) -> Dict[str, bool]:
        """测试所有端点"""
        print(f"🚀 开始测试 FastAPI 服务: {self.base_url}")
        print("=" * 60)
        
        # 执行所有测试
        results = {
            "root": await self.test_root_endpoint(),
            "health": await self.test_health_endpoint(),
            "verify": await self.test_verify_endpoint(),
            "fix": await self.test_fix_endpoint(),
            "verify_and_fix": await self.test_verify_and_fix_endpoint()
        }
        
        # 统计结果
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        print("=" * 60)
        print(f"📊 测试结果汇总:")
        print(f"   总测试数: {total_tests}")
        print(f"   通过数: {passed_tests}")
        print(f"   失败数: {total_tests - passed_tests}")
        print(f"   成功率: {passed_tests/total_tests*100:.1f}%")
        
        if passed_tests == total_tests:
            print("🎉 所有测试通过！")
        else:
            print("⚠️  部分测试失败，请检查服务状态")
        
        return results
    
    def get_test_results(self) -> list:
        """获取详细的测试结果"""
        return self.test_results
    
    def save_test_results(self, filename: str = "test_results.json"):
        """保存测试结果到文件"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.test_results, f, ensure_ascii=False, indent=2)
            print(f"📄 测试结果已保存到: {filename}")
        except Exception as e:
            print(f"❌ 保存测试结果失败: {e}")


async def main():
    """主函数：运行所有测试"""
    # 创建测试器实例
    tester = FastAPITester()
    
    # 运行所有测试
    # results = await tester.test_all_endpoints()
    results = await tester.test_verify_endpoint()
    # results = await tester.test_fix_endpoint()
    # results = await tester.test_verify_and_fix_endpoint()
    
    # 保存测试结果
    save_path = os.path.join(os.path.dirname(__file__), "test_results.json")
    tester.save_test_results(save_path)
    
    return results


if __name__ == "__main__":
    # 直接运行测试
    asyncio.run(main())