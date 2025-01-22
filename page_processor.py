#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Page Processor
Created: 2025-01-22 23:10:15
Author: x9ci
"""

from io import BytesIO
import logging
from typing import List, Dict
from reportlab.pdfgen import canvas
from arabic_handler import ArabicHandler

class PageProcessor:
    def __init__(self, text_processor):
        self.text_processor = text_processor
        self.batch_size = 10
        self.processed_blocks = set()
        self.arabic_handler = ArabicHandler()

    def process_page(self, page_content: List[Dict], page_num: int) -> List[Dict]:
        """معالجة صفحة واحدة"""
        try:
            logging.info(f"معالجة الصفحة {page_num + 1}")
            translated_blocks = []
            text_batch = []
            blocks_to_process = []

            if not page_content:
                logging.warning(f"لا يوجد محتوى في الصفحة {page_num + 1}")
                return []

            # ترتيب المحتوى من أعلى إلى أسفل
            sorted_content = sorted(
                page_content,
                key=lambda x: (-float(x.get('bbox', (0,0,0,0))[1]), float(x.get('bbox', (0,0,0,0))[0]))
            )

            for block in sorted_content:
                if not self._should_process_block(block):
                    continue

                text_batch.append(block.get('text', ''))
                blocks_to_process.append(block)

                if len(text_batch) >= self.batch_size:
                    self._process_batch(text_batch, blocks_to_process, translated_blocks, page_num)
                    text_batch = []
                    blocks_to_process = []

            # معالجة الكتل المتبقية
            if text_batch:
                self._process_batch(text_batch, blocks_to_process, translated_blocks, page_num)

            return translated_blocks

        except Exception as e:
            logging.error(f"خطأ في معالجة الصفحة {page_num + 1}: {str(e)}")
            return []

    def create_translated_overlay(self, translated_blocks: List[Dict], page_num: int, page_size: tuple) -> BytesIO:
        """إنشاء طبقة الترجمة"""
        try:
            packet = BytesIO()
            width, height = float(page_size[0]), float(page_size[1])
            c = canvas.Canvas(packet, pagesize=page_size)
            used_positions = []

            for block in translated_blocks:
                try:
                    if block['type'] != 'text' or not block.get('text'):
                        continue

                    text = block['text']
                    # معالجة النص العربي
                    processed_text = self.arabic_handler.process_text(text)
                    text_width, text_height = self.arabic_handler.get_text_dimensions(text)

                    # حساب الموقع
                    bbox = block['original_bbox']
                    x, y = self._find_optimal_position(
                        bbox, text_width, text_height, used_positions, width, height
                    )

                    # رسم خلفية وكتابة النص
                    self._draw_text_block(c, processed_text, x, y, text_width, text_height)
                    
                    # رسم خط توضيحي
                    self._draw_connection_line(c, x, y, bbox, text_width, text_height, height)
                    
                    used_positions.append((x, y, text_width, text_height))

                except Exception as e:
                    logging.error(f"خطأ في معالجة كتلة نص: {str(e)}")
                    continue

            c.save()
            packet.seek(0)
            return packet

        except Exception as e:
            logging.error(f"خطأ في إنشاء طبقة الترجمة: {str(e)}")
            return self._create_empty_page(width, height)

    def _should_process_block(self, block: Dict) -> bool:
        """التحقق مما إذا كان يجب معالجة الكتلة"""
        if not block.get('text'):
            return False
        
        # تحويل النص إلى سلسلة نصية وتنظيفه
        text = str(block.get('text', '')).strip()
        
        # تجاهل النصوص القصيرة جداً والأرقام
        if len(text) < 3 or text.isdigit():
            return False
            
        return True

    def _process_batch(self, texts: List[str], blocks: List[Dict], translated_blocks: List[Dict], page_num: int):
        """معالجة دفعة من النصوص"""
        try:
            translations = self.text_processor.process_text_batch(texts)
            
            for trans, block in zip(translations, blocks):
                if trans and trans.strip():
                    translated_block = {
                        'text': trans,
                        'original_text': block.get('text', ''),
                        'bbox': block.get('bbox', (0,0,0,0)),
                        'original_bbox': block.get('bbox', (0,0,0,0)),
                        'type': 'text',
                        'page': page_num
                    }
                    translated_blocks.append(translated_block)
                    
        except Exception as e:
            logging.error(f"خطأ في معالجة دفعة الترجمة: {str(e)}")

    def _draw_text_block(self, canvas_obj, text: str, x: float, y: float, width: float, height: float):
        """رسم كتلة النص مع خلفية"""
        # رسم خلفية
        padding = 4
        canvas_obj.saveState()
        canvas_obj.setFillColorRGB(1, 1, 1, 0.9)  # خلفية بيضاء شبه شفافة
        canvas_obj.rect(
            x - padding,
            y - padding,
            width + (2 * padding),
            height + (2 * padding),
            fill=True
        )
        canvas_obj.restoreState()

        # كتابة النص
        canvas_obj.setFont('Arabic', self.arabic_handler.font_size)
        canvas_obj.setFillColorRGB(0, 0, 0)
        canvas_obj.drawRightString(x + width, y + height - 2, text)

    def _draw_connection_line(self, canvas_obj, x: float, y: float, bbox: tuple, 
                            text_width: float, text_height: float, page_height: float):
        """رسم خط يربط النص المترجم بالنص الأصلي"""
        canvas_obj.setStrokeColorRGB(0.7, 0.7, 0.7, 0.3)
        canvas_obj.setLineWidth(0.3)
        
        start_x = x + text_width / 2
        start_y = y + text_height / 2
        end_x = (bbox[0] + bbox[2]) / 2
        end_y = page_height - ((bbox[1] + bbox[3]) / 2)
        
        canvas_obj.line(start_x, start_y, end_x, end_y)

    def _find_optimal_position(self, bbox: tuple, text_width: float, text_height: float, 
                             used_positions: List[tuple], page_width: float, page_height: float) -> tuple:
        """إيجاد أفضل موقع للنص"""
        x = bbox[0]
        y = page_height - bbox[3] - text_height - 5
        
        x = max(5, min(x, page_width - text_width - 5))
        y = max(5, min(y, page_height - text_height - 5))
        
        while self._check_overlap((x, y, text_width, text_height), used_positions):
            y -= text_height + 5
            if y < 5:
                y = page_height - text_height - 5
                x += text_width + 10
                if x + text_width > page_width - 5:
                    x = 5
        
        return x, y

    def _check_overlap(self, current_rect: tuple, used_positions: List[tuple]) -> bool:
        """التحقق من تداخل النصوص"""
        x, y, w, h = current_rect
        for used_x, used_y, used_w, used_h in used_positions:
            if (x < used_x + used_w and x + w > used_x and
                y < used_y + used_h and y + h > used_y):
                return True
        return False

    def _create_empty_page(self, width: float, height: float) -> BytesIO:
        """إنشاء صفحة فارغة"""
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=(width, height))
        c.save()
        packet.seek(0)
        return packet