"""
文件解析模块
"""
import csv
import json
import logging
from typing import List, Dict, Any
from utils import CalculationUtils, FileUtils, ValidationUtils
from config import Config

logger = logging.getLogger(__name__)

class FileParser:
    """文件解析器类"""
    
    @staticmethod
    def parse_csv_file(filepath: str) -> List[List[Any]]:
        """
        解析CSV文件
        
        Args:
            filepath: CSV文件路径
            
        Returns:
            解析后的数据列表
        """
        data = []
        
        # 检测文件编码
        encoding = CalculationUtils.detect_encoding(filepath)
        logger.info(f"检测到文件编码: {encoding}")
        
        # 尝试多种编码
        encodings = [encoding] + [enc for enc in Config.SUPPORTED_ENCODINGS if enc != encoding]
        
        for enc in encodings:
            try:
                with open(filepath, 'r', newline='', encoding=enc) as f:
                    # 尝试检测文件是否有BOM
                    if f.read(1) == '\ufeff':
                        # 重新打开文件，跳过BOM
                        f = open(filepath, 'r', newline='', encoding=enc)
                        f.seek(1)
                    else:
                        f.seek(0)
                    
                    reader = csv.reader(f)
                    
                    # 跳过表头
                    try:
                        header = next(reader)
                        logger.info(f"CSV表头: {header}")
                    except StopIteration:
                        logger.warning("CSV文件为空")
                        break
                    
                    # 处理数据行
                    for row_num, row in enumerate(reader, start=2):
                        if len(row) >= 2:
                            item_name = row[0].strip()
                            quantity_str = row[1].strip()
                            
                            if not item_name or not quantity_str:
                                continue
                            
                            try:
                                boxes, groups, pieces = CalculationUtils.calculate_boxes_and_groups(quantity_str)
                                data.append([item_name, quantity_str, boxes, groups, pieces, "未完成"])
                            except ValueError:
                                logger.warning(f"第{row_num}行数量格式错误: {quantity_str}")
                                continue
                    
                    logger.info(f"成功使用编码 {enc} 解析CSV文件，共{len(data)}行数据")
                    break
                    
            except (UnicodeDecodeError, csv.Error) as e:
                logger.warning(f"编码 {enc} 解析失败: {e}")
                continue
            except Exception as e:
                logger.error(f"解析CSV文件时发生未知错误: {e}")
                continue
        
        if not data:
            logger.error("所有编码尝试都失败，无法解析CSV文件")
            raise ValueError("无法解析CSV文件，请检查文件格式和编码")
        
        return data
    
    @staticmethod
    def parse_sti_file(filepath: str) -> List[List[Any]]:
        """
        解析STI文件（JSON格式）
        
        Args:
            filepath: STI文件路径
            
        Returns:
            解析后的数据列表
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证数据格式
            if not isinstance(data, list):
                raise ValueError("STI文件格式错误：根元素应该是数组")
            
            # 验证每个数据项
            for i, item in enumerate(data):
                if not isinstance(item, list) or len(item) != 6:
                    raise ValueError(f"STI文件格式错误：第{i}项数据格式不正确")
            
            logger.info(f"成功解析STI文件，共{len(data)}行数据")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"STI文件JSON解析失败: {e}")
            raise ValueError(f"STI文件格式错误：{e}")
        except Exception as e:
            logger.error(f"解析STI文件时发生未知错误: {e}")
            raise
