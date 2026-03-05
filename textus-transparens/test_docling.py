from docling.document_converter import DocumentConverter

def test():
    converter = DocumentConverter()
    doc = converter.convert("test.md")
    
    for item, level in doc.document.iterate_items():
        print(getattr(item, "label", "none"), getattr(item, "text", "none"))

test()