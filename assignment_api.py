import pdfplumber
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
import re

@dataclass
class TextualWord:
    x0: float
    x1: float
    text: str

@dataclass
class ExtraTextualWord(TextualWord):
    fontname: str
    size: float

    @property
    def is_bold(self) -> bool:
        return "Bold" in self.fontname


@dataclass
class Chart:
    name: str
    dob: datetime
    has_valid_ekg: bool

    @property
    def age(self) -> float:
        """Calculate the patient's age based on the date of birth."""
        today = datetime.today()
        age = today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
        return age


PagesToWords = Dict[int, List[TextualWord]]
PDFSection = List[List[ExtraTextualWord]]
PagesToExtraWords = Dict[int, List[ExtraTextualWord]]


def pdf_to_dict(pdfplumber_pdf: pdfplumber.PDF) -> PagesToWords:
        """Extract text from a PDF and store it in a PagesToWords dictionary."""
        page_to_words = {}
   
        for page_number, page in enumerate(pdfplumber_pdf.pages):
            words = page.extract_words()
            page_to_words[page_number] = [
                TextualWord(word['x0'], word['x1'], word['text']) for word in words
            ]
   
        return page_to_words




def populate_chart(page_to_words: PagesToWords) -> Chart:
    """Extract patient information from the PDF pages and populate a Chart object."""
    name, dob, has_valid_ekg = None, None, False


    for _, words in page_to_words.items():
      
        for i, word in enumerate(words):
            
            combined_text = word.text.lower().replace(' ', '')
            if i+1<len(words):
                # Extract Patient Name
                if combined_text == "patientname" or (words[i].text.lower() == 'patient' and words[i + 1].text.lower().startswith('name')):
                    try:
                        name_index = i + 2
                        name_parts = []
                        for j in range(name_index, len(words)):
                            current_word = words[j].text
                            if current_word.lower() in ["dob:", "procedures", "lab", "results", "ekg", "radiology"]:
                                break
                            
                            name_parts.append(current_word)
                        name = " ".join(name_parts)
                    
                    except Exception as e:
                        print(f"Error extracting name: {e}")

            # Extract DOB
            if word.text.strip().lower() == "dob:":
                try:
                    dob_index = i + 1
                    if dob_index < len(words):
                        dob_text = words[dob_index].text
                        try:
                            dob = datetime.strptime(dob_text, "%m/%d/%Y")
                        except ValueError as e:
                            print(f"Error parsing DOB: {dob_text}. Exception: {e}")
                except Exception as e:
                    print(f"Error extracting DOB: {e}")

            # Extract EKG Results
            if i < len(words) - 2:
                if words[i].text.lower() == "ekg" and words[i + 1].text.lower() == "results" and words[i + 2].text.lower() == "valid":
                    has_valid_ekg = True

    chart_content = {"name":name,"dob":dob,"has_valid_ekg":has_valid_ekg}

    return Chart(**chart_content)


def pdf_to_extra_dict(pdfplumber_pdf: pdfplumber.PDF) -> List[ExtraTextualWord]:
    """Extract all textual words from the PDF as ExtraTextualWord objects."""
    words = []
    for page in pdfplumber_pdf.pages:
        for word in page.extract_words(extra_attrs=["fontname", "size"]):
            extra_word = ExtraTextualWord(
                x0=word['x0'],
                x1=word['x1'],
                text=word['text'],
                fontname=word['fontname'],
                size=word['size']
            )
            words.append(extra_word)
    return words 
 
def split_to_sections(words: List[ExtraTextualWord]) -> PDFSection:
    """Split the list of ExtraTextualWord into sections where each section starts with a bold word."""
    sections = []
    current_section = []

    for word in words:
        if word.is_bold: 
            if current_section:  
                sections.append(current_section)
            current_section = [word]  
        else:
            current_section.append(word)  

    if current_section:
        sections.append(current_section)

    return sections


def display_sections_for_chart(chart_path,sections):
    print(f"Sections for {chart_path}:\n")
    for i, section in enumerate(sections):
        section_text = " ".join(word.text for word in section)
        print(f"{i + 1}: {section_text}\n")


def extract_sentences_from_pdf(pdf):
    sentences = []
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            page_sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s|\n+', text)
            cleaned_sentences = [sentence.strip() for sentence in page_sentences if sentence.strip()]
            sentences.extend(cleaned_sentences)
    return sentences


def display_sentences(sentences, extra_words):
    bold_titles = {"Patient Name:", "DOB:", "Procedures", "Lab Results", "Radiology Results", "EKG Results"}
    numbered_count = 1

    for sentence in sentences:
       
        for title in bold_titles:
         
            if title in sentence:
               
                title_parts = title.split()
                if all(any(word.text == part and word.is_bold for word in extra_words) for part in title_parts):
                    print(f"{numbered_count}. {sentence}\n")
                    numbered_count += 1
                    break  
        else:
            print(f"{sentence}\n")

def main():
    """Main function to parse the three charts and extract information."""
    chart_paths = ["chart1.pdf", "chart2.pdf", "chart3.pdf"]

    for chart_path in chart_paths:
        with pdfplumber.open(chart_path) as pdf:
            print(f"\nParsing {chart_path}...")
            
            page_to_words = pdf_to_dict(pdf)
            extra_words = pdf_to_extra_dict(pdf)
            
            chart = populate_chart(page_to_words)
       
            print(f"Age={chart.age}\nDob:{chart.dob.strftime('%m/%d/%Y')}\nhas_valid_ekg={chart.has_valid_ekg}\nName:{chart.name}")
            print(f"----------------------------")
            sentences = (extract_sentences_from_pdf(pdf))
            display_sentences(sentences,extra_words)
            
        
        
                    
if __name__ == "__main__":
    main()