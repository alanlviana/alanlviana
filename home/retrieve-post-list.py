import urllib.request
import xml.etree.ElementTree as ET

def main():
   # URL do arquivo XML
   url = "https://alanlviana.com.br/feed.xml"

   xml_content = get_feed_xml(url)
   articles = get_articles_from_xml(xml_content)
   remove_articles_from_readme()
   add_articles_in_readme(articles)

def get_feed_xml(url):
   # Faz a requisição HTTP para obter o conteúdo do arquivo XML
   response = urllib.request.urlopen(url)
   return response.read().decode('utf-8')

def get_articles_from_xml(xml):
   # Analisa o XML e extrai os links
   tree = ET.fromstring(xml)
   articles = []
   for item in tree.iter("item"):
      link = item.find("link").text
      title = item.find("title").text
      articles.append(Article(title, link))
   return articles

def remove_articles_from_readme():
   # Remover linhas de artigos
   with open("./README.md", 'r', encoding="utf8") as fp:
      lines = fp.readlines()

   filtred_lines = []
   remove_lines = False
   for line in lines:
      if line.strip() == "<!--BEGIN_POSTS-->":
         remove_lines = True
         filtred_lines.append(line)
      elif line.strip() == "<!--END_POSTS-->":
         remove_lines = False
         filtred_lines.append(line)
      elif not remove_lines:
         filtred_lines.append(line)
   with open("./README.md", 'w', encoding="utf8") as fp:
      fp.writelines(filtred_lines)         

def add_articles_in_readme(articles):
   with open("./README.md", 'r', encoding="utf8") as fp:
      lines = fp.readlines()

   with open('./README.md', 'w', encoding="utf8") as fp:
      for number, line in enumerate(lines):
         if line.__contains__('<!--BEGIN_POSTS-->'):
            line = line + '\n\n'
            for article in articles:
               line = line + '📰 [' + article.title + "](" +  article.link + ")\n\n"
            line = line + '\n'
         fp.write(line)
      fp.flush()
      fp.close()
            
class Article:
  def __init__(self, title, link):
    self.title = title
    self.link = link

if __name__ == '__main__':
   main()








  






# Imprime a lista de links
