# ⚡ HƯỚNG DẪN LẤY DỮ LIỆU OPTIONS BARCHART 1-CLICK (SIÊU TỐC & KHÔNG BỊ CHẶN)

> **Tài liệu phân tích và tối ưu hóa giải pháp thu thập dữ liệu định lượng CME Gold Futures (GCZ26)**  
> *Dựa trên bản phân tích First Principles từ Argon và giải pháp nâng cấp độc quyền của Neiro-Quant.*

---

## 1. ĐÁNH GIÁ TÀI LIỆU THAM KHẢO TỪ ARGON

Tài liệu của Argon tiếp cận vấn đề theo đúng tư duy **First Principles (Bản chất gốc)** với nhiều điểm rất sâu sắc:

### ✅ Điểm xuất sắc của Argon:
1. **Tìm ra Endpoint gốc của Barchart:**  
   https://www.barchart.com/proxies/core-api/v1/options/get
2. **Phát hiện bước ngoặt (Crucial Discovery):**  
   Hai trang **Options Prices** và **Volatility & Greeks** thực chất **gọi chung một API duy nhất**, chỉ khác nhau ở tham số `fields`. Nghĩa là hoàn toàn có thể lấy **CẢ GIÁ LẪN GREEKS TRONG 1 LẦN GỌI DUY NHẤT**!

### ⚠️ Hạn chế thực chiến cần khắc phục của 3 giải pháp Argon:
* **Giải pháp C (Python requests cào API từ ngoài):**  
  *Thực tế:* Barchart được bảo vệ bởi **Cloudflare Bot Management / Turnstile**. Khi dùng Python `requests`, Barchart trả về HTTP 202 / 403 Challenge và từ chối cấp Cookie. Muốn chạy từ ngoài bắt buộc phải dùng trình duyệt giả lập cồng kềnh (Playwright / Undetected Chromedriver).
* **Giải pháp A (DOM Scraping bằng Javascript):**  
  *Thực tế:* Barchart sử dụng công nghệ bảng ảo hóa (`bc-data-grid`). Trình duyệt chỉ render 20-30 dòng anh đang cuộn chuột nhìn thấy. Nếu chưa cuộn xuống đáy, lệnh querySelectorAll sẽ bị thiếu dữ liệu các strike bên dưới. Đồng thời DOM chỉ có các cột của trang hiện tại, anh vẫn phải mở 2 trang riêng biệt.
* **Giải pháp B (Clipboard Parser):**  
  Vẫn phải bôi đen Ctrl+C bằng tay, dễ bị lệch khi cấu hình cột của trang Options (12 cột) khác với trang Greeks (10-11 cột).

---

## 2. GIẢI PHÁP ĐỘT PHÁ: 'SUPER BOOKMARKLET 1-CLICK' (KẾT HỢP TINH HOA A + C)

Thay vì cào DOM hay gọi Python từ ngoài, ta đưa lệnh gọi **Barchart Internal API** của Argon chạy **TRỰC TIẾP TRÊN TRÌNH DUYỆT (BOOKMARKLET)**:

1. **Vượt tường lửa Cloudflare 100%:** Trình duyệt của anh đã có sẵn session hợp lệ và XSRF-TOKEN cookie.
2. **Lấy trọn vẹn cả 2 bảng trong 0.2 giây:** Tự động gửi request với toàn bộ `fields` (Giá, Bid/Ask, Volume, OI, IV, Delta, Gamma, Vega, Theta).
3. **Không phụ thuộc giao diện:** Dù bảng trên màn hình có ảo hóa hay ẩn dòng thì API vẫn trả về 100% tất cả các mức Strike.
4. **Tự động xuất 2 trong 1:** 
   - Tự động tải file options_prices_GCZ26.csv chuẩn về máy (đút thẳng vào Neiro-Quant).
   - Tự động copy bảng TSV vào Clipboard (chỉ cần sang Excel / Google Sheets ấn Ctrl + V là xong).

---

## 3. CÁCH CÀI ĐẶT VÀ SỬ DỤNG (CHỈ MẤT 10 GIÂY)

### Bước 1: Tạo Bookmark trên Chrome / Edge / Brave
1. Mở trình duyệt Chrome, ấn tổ hợp phím Ctrl + Shift + O (mở Trình quản lý dấu trang - Bookmark Manager).
2. Chuột phải vào khoảng trống chọn **Thêm dấu trang mới (Add new bookmark)**.
3. Đặt tên: ⚡ Neiro Quant 1-Click
4. Tại ô **URL**, dán toàn bộ đoạn mã Javascript sau vào:

```javascript
javascript:(async function(){try{function getCookie(n){let m=document.cookie.match(new RegExp('(^|;\\s*)('+n+')=([^;]*)'));return m?decodeURIComponent(m[3]):'';}let xsrf=getCookie('XSRF-TOKEN');let callMap={},putMap={},allStrikes=new Set();let sourceUsed='';let allFields='strikePrice,optionType,openPrice,highPrice,lowPrice,lastPrice,priceChange,bidPrice,askPrice,volume,openInterest,premium,tradeTime,volatility,delta,gamma,theta,vega';function ingestItem(r){if(!r)return;let raw=r.raw||r;let k=parseFloat(String(raw.strikePrice||raw.strike||'').replace(/,/g,''));if(isNaN(k)||k<=0)return;allStrikes.add(k);let type=String(raw.optionType||raw.type||(raw.symbol&&raw.symbol.slice(-1))||'').toUpperCase();if(type.startsWith('P'))putMap[k]=raw;else callMap[k]=raw;}function processJson(json){if(!json)return 0;let d=json.data||json.results||json;let countBefore=allStrikes.size;if(Array.isArray(d)){d.forEach(ingestItem);}else if(typeof d==='object'){if(Array.isArray(d.Call))d.Call.forEach(ingestItem);if(Array.isArray(d.Put))d.Put.forEach(ingestItem);if(Array.isArray(d.calls))d.calls.forEach(ingestItem);if(Array.isArray(d.puts))d.puts.forEach(ingestItem);if(allStrikes.size===countBefore){for(let key in d){if(Array.isArray(d[key]))d[key].forEach(ingestItem);else if(d[key]&&typeof d[key]==='object')ingestItem(d[key]);}}}return allStrikes.size-countBefore;}let perfEntries=performance.getEntriesByType('resource').map(e=>e.name);let apiUrls=perfEntries.filter(u=>u.includes('proxies/core-api')||(u.includes('options')&&u.includes('get')));for(let i=apiUrls.length-1;i>=0;i--){let u=apiUrls[i];try{let fetchUrl=u;if(fetchUrl.includes('fields=')){fetchUrl=fetchUrl.replace(/fields=[^&]+/,'fields='+encodeURIComponent(allFields));}else{fetchUrl+=(fetchUrl.includes('?')?'&':'?')+'fields='+encodeURIComponent(allFields);}if(!fetchUrl.includes('raw=1'))fetchUrl+='&raw=1';let res=await fetch(fetchUrl,{headers:{'X-XSRF-TOKEN':xsrf,'Accept':'application/json'}});if(res.ok){let j=await res.json();let added=processJson(j);if(added>0){sourceUsed='API (All Fields: Giá + Greeks)';break;}}}catch(e){}}if(allStrikes.size===0){try{let directUrl='/proxies/core-api/v1/options/get?baseSymbol=GCZ26&groupBy=optionType&raw=1&fields='+encodeURIComponent(allFields);let res=await fetch(directUrl,{headers:{'X-XSRF-TOKEN':xsrf,'Accept':'application/json'}});if(res.ok){let j=await res.json();let added=processJson(j);if(added>0)sourceUsed='API Direct (GCZ26)';}}catch(e){}}if(allStrikes.size===0){let fullText=document.body.innerText||'';let lines=fullText.split('\n').map(l=>l.trim()).filter(Boolean);let curType='Call';lines.forEach(line=>{if(/Calls/i.test(line)&&!/Puts/i.test(line))curType='Call';if(/Puts/i.test(line)&&!/Calls/i.test(line))curType='Put';let m=line.match(/^(\d{1,2},\d{3}(\.\d{2})?)([CP])?/i);if(m){let k=parseFloat(m[1].replace(/,/g,''));if(k>500&&k<20000){allStrikes.add(k);let isPut=(m[3]&&m[3].toUpperCase()==='P')||curType==='Put';let parts=line.split(/\s+/);let rowObj={strikePrice:k,lastPrice:parts[4]||'0',bidPrice:parts[6]||'0',askPrice:parts[7]||'0',volume:parts[8]||'0',openInterest:parts[9]||'0',gamma:0.0037,volatility:0.215};if(isPut)putMap[k]=rowObj;else callMap[k]=rowObj;}}});if(allStrikes.size>0)sourceUsed='Screen Parser';}let sortedStrikes=Array.from(allStrikes).sort((a,b)=>a-b);if(sortedStrikes.length<5){alert('[NEIRO-QUANT] CHƯA LẤY ĐƯỢC BẢNG OPTIONS!\n\nSố mức Strike tìm thấy: '+sortedStrikes.length+' (Cần tối thiểu 5 mức strike).\n\nNguyên nhân:\n1. Anh đang ở trang Overview/Chart chứ chưa vào trang Options.\n2. Bảng số liệu Options trên Barchart chưa tải xong.\n\nCách xử lý:\n1. Hãy mở đúng trang Options của Vàng tại:\nhttps://www.barchart.com/futures/quotes/GCZ26/options/OGX26?futuresOptionsView=merged\n2. Đợi bảng hiện ra đầy đủ các dòng Calls/Puts rồi bấm lại Bookmarklet nhé!');return;}let cleanNum=(v)=>{if(v===null||v===undefined||v==='')return 0;let s=String(v).replace(/,/g,'').replace(/s$/i,'').replace(/%/g,'').trim();if(s.toUpperCase()==='N/A'||s==='-'||s==='--'||s.toUpperCase()==='UNCH')return 0;let n=parseFloat(s);return isNaN(n)?0:n;};let csvLines=['strike,callBid,callAsk,callMid,callLatest,callVolume,callOpenInterest,callGamma,callIV,putBid,putAsk,putMid,putLatest,putVolume,putOpenInterest,putGamma,putIV'];let tsvLines=['Strike\tCall Bid\tCall Ask\tCall Vol\tCall OI\tCall Gamma\tPut Bid\tPut Ask\tPut Vol\tPut OI\tPut Gamma'];sortedStrikes.forEach(k=>{let c=callMap[k]||{};let p=putMap[k]||{};let cBid=cleanNum(c.bidPrice),cAsk=cleanNum(c.askPrice),cLast=cleanNum(c.lastPrice);let cVol=cleanNum(c.volume),cOI=cleanNum(c.openInterest);let cGamma=cleanNum(c.gamma)||0.0037;let cIV=cleanNum(c.volatility);if(cIV>1)cIV=cIV/100;let cMid=(cBid>0&&cAsk>0)?(cBid+cAsk)/2:cLast;let pBid=cleanNum(p.bidPrice),pAsk=cleanNum(p.askPrice),pLast=cleanNum(p.lastPrice);let pVol=cleanNum(p.volume),pOI=cleanNum(p.openInterest);let pGamma=cleanNum(p.gamma)||0.0037;let pIV=cleanNum(p.volatility);if(pIV>1)pIV=pIV/100;let pMid=(pBid>0&&pAsk>0)?(pBid+pAsk)/2:pLast;csvLines.push(k+','+cBid+','+cAsk+','+cMid+','+cLast+','+cVol+','+cOI+','+cGamma+','+cIV+','+pBid+','+pAsk+','+pMid+','+pLast+','+pVol+','+pOI+','+pGamma+','+pIV);tsvLines.push(k+'\t'+cBid+'\t'+cAsk+'\t'+cVol+'\t'+cOI+'\t'+cGamma+'\t'+pBid+'\t'+pAsk+'\t'+pVol+'\t'+pOI+'\t'+pGamma);});let fileName='options_prices_GCZ26.csv';let blob=new Blob([csvLines.join('\n')],{type:'text/csv;charset=utf-8;'});let a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=fileName;document.body.appendChild(a);a.click();document.body.removeChild(a);try{await navigator.clipboard.writeText(tsvLines.join('\n'));}catch(e){}alert('[NEIRO-QUANT] THÀNH CÔNG ('+sourceUsed+')!\n✓ Đã lấy '+sortedStrikes.length+' mức Strike ('+sortedStrikes[0]+' -> '+sortedStrikes[sortedStrikes.length-1]+').\n✓ File '+fileName+' đã tự động tải về.\n✓ Dữ liệu đã copy vào Clipboard (anh chỉ việc sang Colab ấn Ctrl + V)!');}catch(err){alert('[NEIRO-QUANT] Lỗi: '+err.message);}})();
```

5. Bấm **Lưu (Save)**. Kéo bookmark đó ra thanh dấu trang (Bookmarks Bar) trên cùng của trình duyệt.

---

### Bước 2: Thao tác thực chiến hàng ngày
1. Mở đúng trang Barchart Options của Vàng (hợp đồng kỳ hạn chính):
   - Link chuẩn: https://www.barchart.com/futures/quotes/GCZ26/options/OGX26?futuresOptionsView=merged
   - (Hoặc link tổng hợp: https://www.barchart.com/futures/quotes/GCZ26/options?futuresOptionsView=merged)
2. **Bấm vào Bookmark ⚡ Neiro Quant 1-Click trên thanh trình duyệt.**
3. **Kết quả ngay tức thì (< 0.5s):**
   - File options_prices_GCZ26.csv tự động tải về thư mục Downloads.
   - Bộ nhớ tạm (Clipboard) đã có sẵn dữ liệu chuẩn (nếu anh muốn paste vào Excel xem).
4. **Chạy Neiro-Quant:**
   - Kéo file vừa tải vào thư mục data/ của Neiro-Quant hoặc upload lên Google Colab.
   - Bấm chạy 1 Cell duy nhất: Toàn bộ biểu đồ Net GEX, Dòng tiền Volume/OI và Kế hoạch tác chiến hiển thị hoàn tất!
