#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arabic Text Handler
Created: 2025-01-22 20:35:14
Author: x9ci
"""

import os
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class ArabicHandler:
    def __init__(self):
        self.font_size = 14
        self.font_name = 'Arabic'
        self.initialize_fonts()

    def initialize_fonts(self):
        """تهيئة الخطوط العربية"""
        try:
            font_paths = [
                "/usr/share/fonts/truetype/arabic/Amiri-Regular.ttf",
                "./fonts/Amiri-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                "./fonts/FreeSans.ttf"
            ]

            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        # التحقق مما إذا كان الخط مسجل مسبقاً
                        if self.font_name not in pdfmetrics.getRegisteredFontNames():
                            pdfmetrics.registerFont(TTFont(self.font_name, font_path))
                        print(f"تم تحميل الخط: {font_path}")
                        return True
                    except Exception as e:
                        print(f"خطأ في تحميل الخط {font_path}: {e}")
                        continue

            print("تحذير: لم يتم العثور على خط عربي مناسب")
            return False

        except Exception as e:
            print(f"خطأ في تهيئة الخطوط: {e}")
            return False

    def process_text(self, text):
        """معالجة النص العربي"""
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except Exception as e:
            print(f"خطأ في معالجة النص العربي: {e}")
            return text

    def get_text_dimensions(self, text):
        """حساب أبعاد النص"""
        try:
            processed_text = self.process_text(text)
            width = len(processed_text) * self.font_size * 0.6
            height = self.font_size * 1.5
            return width, height
        except Exception as e:
            print(f"خطأ في حساب أبعاد النص: {e}")
            return 0, 0