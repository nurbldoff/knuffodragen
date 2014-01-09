#!/usr/bin/ruby1.8
# -*- coding: emacs-mule -*-

require 'cgi'
require "tempfile"
require 'parsedate'

$version = 1.0

$pagesDir = "wiki/"
$templDir = "templates/"
$startPage = "KnuffoDragen"

class Page
  @@total = 0
  @@editPage = (IO.readlines($templDir+"edit.html")).join
  @@searchPage = (IO.readlines($templDir+"search.html")).join
  @@historyPage = (IO.readlines($templDir+"history.html")).join
  @@oldPage = (IO.readlines($templDir+"oldpage.html")).join
  @@errorPage = (IO.readlines($templDir+"error.html")).join
  @@pageHead = (IO.readlines($templDir+"head.html")).join
  @@pageFoot = (IO.readlines($templDir+"foot.html")).join
  def initialize(name, text, time)
    @name = name
    @text = text
    @time = time
    @age = 0
  end
  #attr_writer :name
  #attr_writer :text

  def load(name)
    if findFile($pagesDir, name)
      file = File.open($pagesDir+name)
      @name = name
      @text = ((file.readlines(nil)).join).chomp
      @time = file.mtime
      return true
    else
      return false
    end
  end

  def save(small)
    newPage = !findFile($pagesDir, @name)
    @text = @text.gsub(/\^M/,"")
    if !findFile($pagesDir, @name)
      file = File.open($pagesDir+@name, "w")
      pTime = @time
    else
      file = File.open($pagesDir+@name)
      pTime = file.mtime.to_s
    end
    file.close 
    if @time == pTime
      diff = Diff.new(@name, "", "", ENV['REMOTE_ADDR'])
      res = diff.make(@text)
      if res != 0 then
	diff.save
      end
      File.open("#{$pagesDir + @name}", "w") do |file|
	file.syswrite(@text)
      end
      if not small
	File.open("#{$pagesDir + "changes.log"}", "a") do |file|
	  file.syswrite((newPage ? "!" : "") + @name + "\n" + Time.new.to_i.to_s + "\n" + diff.host + "\n\n")
	end
      end
      return true
    else
      return false
    end
  end

  def display
    puts @name
    puts @text
  end

  def show
    puts replBrks(@@pageHead) + (formatPage(@text)) + replBrks(@@pageFoot)
  end

  def edit
    puts replBrks(@@editPage)
  end

  def edit2(name, text, time)
    puts replBrks(@@editPage)
  end

  def error
    puts replBrks(@@errorPage)
  end

  def showSearch
    @text = activateWords(@text)
    puts activateCommands((replBrks(@@searchPage)))
  end

  def showHistory
    diffs = readDiffs(@name)
    len = diffs.length
    diffs.each_index { |ind|
      @text = @text + "<a href=?show=#{diffs[ind].name}+#{ind}>" + (diffs[ind].time).to_s + "</a> - " + diffs[ind].host + " - <a href=?restore=#{diffs[ind].name}+#{ind}>ÅÂterstÅ‰ll</a>" + "<br>"
    }
    puts activateCommands((replBrks(@@historyPage)))
  end

  def showChanges(n)
    changes = readChanges("changes.log", n)
    len = changes.length
    str = ""
    changes.each_index { |ind|
      str = str + 
        changes[ind].name + "+0" + (changes[ind].new ? " <b>(NY!)</b> - " : " - ") + fmtTime(changes[ind].time.to_i).to_s + " sedan - (<i>" + sweDate(changes[ind].time.to_i) + "</i>)<br>"
#        " - (" + changes[ind].host + ")<br>"
    }
    return str
  end

  def getOld(index)
    @age = index
    diffs = readDiffs(@name)
    if index < diffs.length
      for i in 0..index
	@text = diffs[i].apply(@text, 0)
      end
      @text = diffs[index].applyReverse(@text)
      @time = (diffs[index].time).to_s
      return true
    else 
      return false
    end
  end

  def showOld(index)
    if index == 0
      show
    else 
      @text = formatPage(@text)
      puts activateCommands((replBrks(@@oldPage)))
    end
  end

  def restoreOld(index)
    getOld(index)
    save
    show
  end

  def replBrks(str)
    return str.gsub(/\#\{(.*?)\}/) {
      match = $1
      case match
      when "@name" then @name 
      when "@ename" then CGI.escape(@name)
      when "@text" then @text
      when "@time" then @time
      when "@age" then @age
      when "prev" then @age + 1
      when "next" then @age - 1
      when "version" then $version
      end
    }
  end

  def activateCommands(str)
    return str.gsub(/\[\[(.*?)\]\]/) {
      match = $1
      case match
      when "sourcecode"
      	f = File.open($0)
        txt = (f.readlines(nil).join).chomp	
      	"\n==\n" + txt + "\n==\n"
      when "namesearch" 
	%Q!<form action=""><input type="text" size="40" name="search" value=""></form>!
      when /namesearch=(.*)/ 
	searchWord($1).join(", ")
      when "wordsearch"
	%Q!<form action=""><input type="text" size="40" name="fsearch" value=""></form>!
      when /wordsearch=(.*)/ 
	searchFull($1, @name).join(", ")
      when /header=(.*)/ 
	searchFirstLine($1, @name).join(", ")
      when /changes(\d*)/
	"<blockquote>" + showChanges($1.to_i) + "</blockquote>"
      when /image=(.*)/
	%Q!<img src="#{$1}">!
      when /random=(\d*)/ 
	(rand($1.to_i)+1).to_s
      when /html=(.*)/
        "<#{$1}>"
      end
    }
  end


  def styleList(str)
    re = %r{\n?^([*0? ])(.*?)\n*(^[^>\n*0?! ]|^\.$|\Z)}m
    str.gsub!(re) {
      start = $1
      list = $1 + $2
      tmp = $2
      if $3 == "."
	ending = ""
      else
	ending = $3
      end
      list.gsub!(/^\?/m, "<dt>")
      list.gsub!(/^!/m, "<dd>")
      list.gsub!(/^[*0]/m, "<li>")
      list.gsub!(/^ /m, "")
      case start
      when "+"
	'<h3>' + tmp + "</h3>" + ending
      when " "
	"<blockquote>" + list + "\n</blockquote>" + ending
      when "*"
	"<ul>" + styleList(list) + "\n</ul>" + ending
      when "0"
	"<ol>" + styleList(list) + "\n</ol>" + ending
      when "?"
	"<dl>" + styleList(list) + "\n</dl>" + ending
      end
    }
    str
  end


  def styleComment(str,lev)
    re = %r{^>(.*?)(^[^>\n]|\Z)}m
    col = ["a00000", "705000", "008000", "006080", "0000a0", "700070"]
    str.gsub(re) {
      ending = $2
      body = $1.gsub(/\n>/, "\n")
      %Q!<table width="100%" border=0 cellpadding=0 cellspacing=0><tr><td width=1>&nbsp;&nbsp;&nbsp;</td><td><font color="##{col[lev%6]}">! + styleComment(body, lev + 1) + "</font></td></tr></table>" + ending
    }
  end


  def activateWords(str)
    expr = /([^A-ZÅ≈ÅƒÅ÷a-zÅÂÅ‰Åˆ0-9]|\A)(([A-ZÅ≈ÅƒÅ÷]{1,2}[a-zÅÂÅ‰Åˆ0-9]+){2,})(\+\d+)?([^A-ZÅ≈ÅƒÅ÷a-zÅÂÅ‰Åˆ0-9]|$)/m
    return (str.gsub(expr) {
	      if findFile($pagesDir, $2)
                age = $4 || ""
		$1 + %Q!<a href="?show=#{CGI.escape($2)+age}">#{$2}</a>#{$5}! 
	      else
		$1 + %Q!#{$2}<a href="?edit=#{CGI.escape($2)}">?</a>#{$5}!
	      end
	    }).gsub(%r{([^"])((http|ftp|mailto):[-a-zÅÂÅ‰ÅˆA-ZÅ≈ÅƒÅ÷0-9./~=+:?@_&]*)}, '\1<a href=\2>\2</a>')
  end


  def styleText(str)
    re = Regexp.new(%r{(\$\$|==|''|\#\#|__|,,|\^\^|\+\+|--)(\S|\S.*?\S)(\1|\n|\Z)|([_^]\{)(\S|\S.*?\S)(\})})  
    #|(\[\[)(.*?)(\]\])})   
    str.gsub(re) {
      if $1 
        start = $1
        body = $2
        ending = $3
      else
        start = $4
        body = $5
        ending = $6
      end
      if ending != "\n"
        ending = ""
      end
        
      case start
      when "[[" then start + body + ending
      when "==" then "<code>" + body + "</code>" + ending
      when "''" then "<i>" + styleText(body) + "</i>" + ending
      when "##" then "<b>" + styleText(body) + "</b>" + ending
      when "__" then "<u>" + styleText(body) + "</u>" + ending
      when "\$\$" then start + body + start
      when "\^\^" then "<sup>" + styleText(body) + "</sup>" + ending
      when ",," then "<sub>" + styleText(body) + "</sub>" + ending
      when "\+\+" then '<font size="+1">' + styleText(body) + "</font>" + ending
      when "--" then '<font size="-1">' + styleText(body) + "</font>" + ending
      when "_\{" then "<sub>" + body + "</sub>" + ending
      when "^\{" then "<sup>" + body + "</sup>" + ending
      end
    }
  end

  def styleSub(str)
    expr2 = Regexp.new(%r{([_|^])\{(.*?)\}})
    return str.gsub(expr2) {
      del = $1.dup
      match = $2.dup

      match.gsub!(/[_^]/," ")
      case del
      when "^" then "<sup>#{match}</sup>"
      when "_" then "<sub>#{match}</sub>"
      end
    }
  end

  
  def styleTable(str)
    table_re = Regexp.new(%r{(^(\|\|(.*?)\|\|\n)+)})
    #row_re = %r{^(\|\|(.*?))+\|\|$}
    str.gsub!(table_re) {
      rows = $1.split("\n")
      rows.map! { |row|
        #row.gsub!(%r{\|(\S[^|]*)\|}) {"<td align=left bgcolor=#ffffff>"+$1+"</td>"}
        #row.gsub!(%r{\|(\s[^|]*\s)\|}) {"<td align=center>"+$1+"</td>"}
        #row.gsub!(%r{\|(\s[^|]*\S)\|}) {"<td align=right>"+$1+"</td>"}
        "<tr><td bgcolor=#ffffff>"+row[2..-3].gsub("||", "</td><td bgcolor=#ffffff>")+"</td></tr>"
        #"<tr>"+row+"</tr>"
      }
      "<table border=0 cellspacing=1 cellpadding=2 bgcolor=#000000>"+rows.join()+"</table>"
    }
    tabular_re = Regexp.new(%r{^\|\|\n(.*?)^\|\|\n})
    str.gsub!(tabular_re) {
      rows = $1.split("\n")
      rows.map! { |row|
        "<tr><td>"+row.gsub(" {2,}|\t", "</td><td>")+"</td></tr>"
      }
      "<table border=1 cellspacing=0 cellpadding=2>"+rows.join()+"</table>"
    }
    return str
  end



  def formatPage(str)
    re = %r{^==$\n?}m
    tmp = str.split(re)
    tmp.each_index {|i|
      if i%2 == 0
	tmp2 = tmp[i].split("\\\\")
	tmp2.each_index {|j|
	  if j%2 == 0
	    tmp2[j] =
              activateWords(activateCommands((styleTable(styleText(styleComment(styleList(tmp2[j].gsub("<->","&harr;").gsub("<-","&larr;").gsub("->", "&rarr;").gsub("<=>","&hArr;").gsub("=>", "&rArr;").gsub("=>", "&rArr;").gsub("<", "&lt;").gsub(/([>\n])--[-]*\n?/,'\1<hr>').gsub(" --- ", "&mdash;")),0)))))).gsub(/([>\n])-----?$/,'\1<hr>\n').gsub("\n","<br>\n")
          else
            tmp2[j] = tmp2[j].gsub("$", "<span>$</span>")
	  end
	}
	tmp[i] = tmp2.join
      else
	tmp[i] = "<pre>" + tmp[i].gsub("<", "&lt;") + "</pre>"
      end
    }
    tmp.join
  end


end

def findFile(dir, name)
  files = Dir.entries(dir)
#  files.each {|f| puts f}
  return files.include?(name)
end

def searchWord(wOrd)  
  files = Dir.entries($pagesDir)
  res = Array.new
  files.each { |file|
    if (file.downcase).index(wOrd.downcase)
      if !(file.downcase).index(".")
	res.push(file)
      end
    end
  }
  return res
end

def searchFull(str, ref)
  #print %Q!grep -l "#{str}" #{$pagesDir}* > grepres.txt!
  system(%Q!grep -E -l '#{str}' #{$pagesDir}* > grepres.txt!)
  if $?!=7 
    file = File.open("grepres.txt")
    arr = Array.new
    names = (file.readlines(nil)).join.split(" ")
    #system("rm grepres.txt")
    names.each { |a|
      #print a + "<br>"
      a =~ %r{.*/(.*)}
      a = $1
      if not a.index(".") and (a != ref)
	arr.push(a)
      end
    }
    arr.sort
  else 
    ["Oops... nÅÂt Å‰r fel! Bugg! HjÅ‰lp!"]
  end
end

def searchFirstLine(str, ref)
  #print %Q!grep -l "#{str}" #{$pagesDir}* > grepres.txt!
  system(%Q!egrep -l '^WikiKategorier: #{str}' #{$pagesDir}* > grepres.txt!)
  if $?==0 
    file = File.open("grepres.txt")
    arr = Array.new
    names = (file.readlines(nil)).join.split(" ")
    #system("rm grepres.txt")
    names.each { |a|
      #print a + "<br>"
      a =~ %r{.*/(.*)}
      a = $1
      if not a.index(".") and (a != ref)
	arr.push(a)
      end
    }
    arr.sort
  else 
    ["Oops... nÅÂt Å‰r fel! Bugg! HjÅ‰lp!"]
  end
end

def searchFull0(str)
  files = Dir.entries($pagesDir)
  res = Array.new
  files.each { |file|
    if !(file.downcase).index(".")
      system("grep -q '#{str}' #{$pagesDir + file}")
      if $?==0 then
	res.push(file)
      end
    end
    }
  return res
end
  

class Diff

  @@tmpOut = Tempfile.new("tmpOut")
  @@tmpStr = Tempfile.new("tmpStr")

  def initialize(name, time, data, host)
    @name = name
    @time = time
    @data = data 
    @host = host
  end

  attr_reader :name, :time, :data, :host

  def make(str)
    @@tmpStr=Tempfile.new("tmpStr")
    @@tmpStr.syswrite(str)
    @@tmpStr.close
    f = File.open("testStr2","w")
    f.puts(str)
    f.close
    #puts "/home/agrajag/bin/diff -u #{$pagesDir + @name} #{@@tmpStr.path} > #{@@tmpOut.path}"
    system("diff testStr2 #{$pagesDir + @name} > diffOut")
    
    f=File.open("diffOut","r")
    @data = (f.readlines).join
    @time = Time.new
    f.close
    return $?
  end

  def save
    file = File.open($pagesDir + @name + ".diffs", "a")
    file << (@time.to_s + "\n" + @host + "\n" + @data + "***\n")
    file.close
  end

  def apply(str, color)
    @@tmpStr=Tempfile.new("tmpStr")
    @@tmpStr.syswrite(@data)
    @@tmpStr.close
    f = File.open("testDiff","w")
    f.puts(@data)
    f.close
    @@tmpOut=Tempfile.new("tmpOut")
    @@tmpOut.syswrite(str)
    @@tmpOut.close
    f = File.open("testStr","w")
    f.syswrite(str)
    f.close
    system("patch --verbose -l #{@@tmpOut.path} #{@@tmpStr.path} > patchOut")
    @@tmpOut.open
    patched = (@@tmpOut.readlines).join
    @@tmpOut.close
    return patched
  end

  def applyReverse(str)
    #@data = @data.gsub(%r{^< (.*?)$}) {"< <<font style='BACKGROUND-COLOR: yellow'>#{$1}<</font>"}

    i = 0
    @data = @data.gsub(%r{([dc]\d+)\n(([<>].*\n)+)}) {
      #|i|
      command = $1
      if command[0] == ?d
        col="#ffff00"
      else
        col="#ffddff"
      end
      body=$2.gsub!(%r{^([<>] [->+|*0 ]*)(.*?)$}) {"#{$1}\[\[html=a href=\#change#{i}\]\]\[\[html=/a\]\]\[\[html=font style='BACKGROUND-COLOR: #{col}'\]\]#{$2}\[\[html=/font\]\]"}
      command + "\n" + body
      #i=i+1
  
    }
    @@tmpStr=Tempfile.new("tmpStr")
    @@tmpStr.syswrite(@data)
    @@tmpStr.close
    f = File.open("testDiff","w")
    f.puts(@data)
    f.close
    @@tmpOut=Tempfile.new("tmpOut")
    @@tmpOut.syswrite(str)
    @@tmpOut.close
    f = File.open("testStr","w")
    f.syswrite(str)
    f.close
    system("patch -R --verbose -l #{@@tmpOut.path} #{@@tmpStr.path} > patchOut")
    @@tmpOut.open
    patched = (@@tmpOut.readlines).join
    @@tmpOut.close
    return patched
  end
end

def fmtTime(oldt)
  newt = Time.now.to_i
  time = Time.at(newt - oldt)
  return (time.year > 1970 ? (time.year - 1970).to_s + " ÅÂr, " : "") + 
   	 (time.yday > 1 ? (time.yday - 1).to_s + " d, " : "") + 
         (time.hour > 1 ? (time.hour - 1).to_s + "h, " : "") +
	 (time.min.to_s + "m")
end

def sweDate(t)
  time= Time.at(t)
  wdays = ["sÅˆn", "mÅÂn", "tis", "ons", "tor", "fre", "lÅˆr"]
  months = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]
  return time.strftime("%H:%M") + ", " + wdays[time.wday] + " " + time.day.to_s + " " + months[time.mon - 1] + ", " + time.year.to_s
end


def readDiffs(fileName)
  file = File.open($pagesDir + fileName + ".diffs")  
  lines = file.readlines("***\n")
  diffs = []
  lines.each {|line|
    /(.*?\n)(.*?\n)((.*\n)*)\*\*\*/.match(line)
    diffs.push(Diff.new(fileName, $1, $3, $2))
  }
  return diffs.reverse
end

class Change
  def initialize(name, time, host, new)
    @name = name
    @time = time
    @host = host
    @new = new
  end
  attr_reader :name, :time, :host, :new
end

def readChanges(fileName, len)
  file = File.open($pagesDir + fileName)  
  lines = file.readlines("\n\n").reverse.indexes(0...len)[0]
  changes = []
  lines.each { |line|
    /(.*?)\n(.*?)\n(.*?)\n\n/.match(line)
    name = $1.dup
    if $1[0].chr == "!"
      new = true
      name = name.slice(1..-1)
    else
      new = false
    end
    changes.push(Change.new(name, $2, $3, new))
  }
  return changes
end

cgi = CGI.new("html4")

com = cgi.keys

#diffs = readDiffs("EnTorsk")
#puts diffs[0]

#saveDiff("snabb/EnTorsk", "snabb/EnTorsk", strTmp, diffTmp)

case com[0]
when "show"
  print "Content-type: text/html; charset=iso-8859-1\r\nExpires: Thu, 01 Dec 1994 16:00:00 GMT\r\n\r\n"
  page = Page.new("","","")  
  args = (cgi["show"]).to_s
  if (args.split).length == 1 then
    pName = args
    pNum = -1
  else 
    pName = (args.split)[0]
    pNum = (args.split)[1].to_i
  end
  if page.load(pName) then 
    if pNum >= 0
      if !page.getOld(pNum)
	page = Page.new(pName, "NÅÂgon sÅÂ gammal version av sidan <b>#{pName}</b> finns inte.", "")
	page.error
      else
	page.showOld(pNum)
      end
    else
      page.show
    end
  else
    page = Page.new(pName, "Sidan <b>#{pName}</b> finns inte.", "")
    page.error
  end
when "edit"
  puts "Content-type: text/html; charset=iso-8859-1\r\nExpires: Thu, 01 Dec 1994 16:00:00 GMT\r\n\r\n"
  pName = (cgi["edit"]).to_s
  re = Regexp.new(/([^A-ZÅ≈ÅƒÅ÷a-zÅÂÅ‰Åˆ0-9]|\A)(([A-ZÅ≈ÅƒÅ÷]{1,2}[a-zÅÂÅ‰Åˆ0-9]+){2,})/, Regexp::MULTILINE)
  if pName =~ re
    page = Page.new("","","")
    if page.load(pName) then page.edit
    else 
      page = Page.new(pName, "", Time.new)
      page.edit
    end
  else
    page = Page.new(pName, "<b>#{pName}</b> Å‰r inte godkÅ‰nt som wiki-ord!", "")
    page.error
  end
when "name"
  pName = (cgi["name"]).to_s
  if cgi["small"].to_s == "true"
    small = true
  else
    small = false
  end
  txt = (cgi["text"]).gsub("\r","")
#  res = CGI.parse($stdin.gets)
  page = Page.new(pName, txt, (cgi['time']).to_s)
  if page.save(small)
    puts "Location: ?show=" + CGI.escape("#{pName}") + "\r\n\r\n"
  else
    puts "Location: ?show=" + CGI.escape("SidanÅƒndrad") + "\r\n\r\n"
  end
when "search"
  puts "Content-type: text/html; charset=iso-8859-1\r\nExpires: Thu, 01 Dec 1994 16:00:00 GMT\r\n\r\n"
  sTerm = (cgi["search"]).to_s
  pages = searchWord(sTerm)
  page = Page.new(sTerm, pages.join(", "), "")
  page.showSearch
when "fsearch"
  puts "Content-type: text/html; charset=iso-8859-1\r\nExpires: Thu, 01 Dec 1994 16:00:00 GMT\r\n\r\n"
  sTerm = (cgi["fsearch"]).to_s
  pages = searchFull(sTerm, "")
  page = Page.new(sTerm, pages.join(", "), "")
  page.showSearch
when "history"
  puts "Content-type: text/html; charset=iso-8859-1\r\nExpires: Thu, 01 Dec 1994 16:00:00 GMT\r\n\r\n"
  pName = (cgi["history"]).to_s
  page = Page.new(pName, "", "")
  page.showHistory
when "restore"
  puts "Content-type: text/html; charset=iso-8859-1\r\nExpires: Thu, 01 Dec 1994 16:00:00 GMT\r\n\r\n"
  args = cgi["restore"].to_s
  pName = (args.split)[0]
  index = (args.split)[1].to_i
  page = Page.new(pName, "", "")
  if page.load(pName) then
    page.restoreOld(index)
  end
when "changes"
  puts "Content-type: text/html; charset=iso-8859-1\r\nExpires: Thu, 01 Dec 1994 16:00:00 GMT\r\n\r\n"
  arg = cgi["changes"].to_s.to_i
  page = Page.new(pName, "", "")
  page.showChanges(arg)
when nil
   puts "Content-type: text/html; charset=ISO-8859-1\r\nExpires: Thu, 01 Dec 1994 1
6:00:00 GMT\r\n\r\n"
   page = Page.new("","","")  
   page.load($startPage)
   page.show
else
  puts "Content-type: text/html; charset=iso-8859-1\r\nExpires: Thu, 01 Dec 1994 16:00:00 GMT\r\n\r\n"
  page= Page.new("","","")
  page.load("FelaktigtKommando")
  page.show
end
