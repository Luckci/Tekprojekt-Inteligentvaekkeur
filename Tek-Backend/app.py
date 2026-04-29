# app.py
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pydantic import BaseModel
import uvicorn
import socket

# Import your helpers
from schedule import setup_driver, login, subject_mapping

app = FastAPI()

# ---------------------- helpers ----------------------
def iso_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def parse_time_ensure_seconds(t: Optional[str]) -> Optional[str]:
    if not t:
        return None
    return t if len(t) == 8 else (t + ":00" if len(t) == 5 else t)

def simple_hash(s: str) -> str:
    h = 0
    for ch in s:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    return str(h)

def close_all_popups(driver, wait: WebDriverWait, max_rounds: int = 5) -> None:
    """Close Vaadin modals via their closeboxes; JS click avoids intercepts."""
    for _ in range(max_rounds):
        closeboxes = driver.find_elements(By.CSS_SELECTOR, "div.v-window-closebox")
        if not closeboxes:
            try:
                driver.switch_to.active_element.send_keys(Keys.ESCAPE)
            except Exception:
                pass
            closeboxes = driver.find_elements(By.CSS_SELECTOR, "div.v-window-closebox")
            if not closeboxes:
                return

        clicked = False
        for btn in closeboxes:
            try:
                driver.execute_script("arguments[0].click();", btn)
                clicked = True
            except Exception:
                try:
                    btn.click()
                    clicked = True
                except Exception:
                    pass

        if clicked:
            try:
                WebDriverWait(driver, 3).until_not(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.v-window"))
                )
            except Exception:
                pass
        else:
            return

def navigate_to_schedule_service(driver, wait: WebDriverWait) -> None:
    close_all_popups(driver, wait)
    wait.until(EC.presence_of_element_located((
        By.CLASS_NAME, "v-absolutelayout-wrapper-ugeskema-skemabrik-element"
    )))

def get_week_signature(driver) -> str:
    try:
        el = driver.find_element(By.XPATH, "//div[contains(@class,'v-label') and contains(., 'Uge')]")
        txt = el.text.strip()
        if txt:
            return txt
    except Exception:
        pass
    blocks = driver.find_elements(By.CSS_SELECTOR, "div.v-absolutelayout-wrapper")
    first_style = blocks[0].get_attribute("style") if blocks else "none"
    return f"blocks:{len(blocks)}|first:{first_style}"

def click_next_week_and_wait(driver, wait: WebDriverWait, current_sig: str) -> Optional[str]:
    close_all_popups(driver, wait)
    next_btn = wait.until(EC.element_to_be_clickable((
        By.XPATH,
        "//div[@role='button' and contains(@class, 'v-button-link') and .//img[contains(@src, 'arrow-right.png')]]"
    )))
    try:
        driver.execute_script("arguments[0].click();", next_btn)
    except Exception:
        next_btn.click()
    try:
        WebDriverWait(driver, 12).until(lambda d: get_week_signature(d) != current_sig)
        new_sig = get_week_signature(driver)
        close_all_popups(driver, wait)
        return new_sig
    except Exception:
        return None

def weekday_date_map(week_offset: int) -> Dict[int, str]:
    today = datetime.now()
    start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    return {i: iso_date(start + timedelta(days=i)) for i in range(5)}

def extract_week_events_service(driver, wait: WebDriverWait, weeks: int, class_name_hint: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    navigate_to_schedule_service(driver, wait)
    current_sig = get_week_signature(driver)

    for offset in range(weeks):
        dates = weekday_date_map(offset)
        blocks = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.v-absolutelayout-wrapper")))
        for block in blocks:
            try:
                cls = block.get_attribute("class") or ""
                style = block.get_attribute("style") or ""
                m = re.search(r"left:\s*([0-9.]+)%", style); day_idx = 0
                if m:
                    left = float(m.group(1)); day_idx = min(int(left // 20), 4)
                date = dates.get(day_idx)

                # Lessons
                subj_el = block.find_elements(By.CLASS_NAME, "v-label-text-ellipsis")
                if not subj_el:
                    continue
                raw_subject = subj_el[0].text.strip()
                short = raw_subject.split(" ")[-1]
                subject = subject_mapping.get(short, short)

                time_text = None
                try:
                    time_text = block.find_element(
                        By.XPATH, ".//div[contains(@class, 'v-label-small') and contains(text(), '-')]"
                    ).text.strip()
                except Exception:
                    pass

                start_t = end_t = None
                if time_text:
                    parts = re.split(r"[-–]", time_text)
                    if len(parts) >= 2:
                        start_t = parse_time_ensure_seconds(parts[0].strip())
                        end_t   = parse_time_ensure_seconds(parts[1].strip())

                room = None
                room_els = block.find_elements(
                    By.XPATH, ".//div[contains(@class, 'v-label-small') and contains(text(), 'MU')]"
                )
                if room_els: room = room_els[0].text.strip()

                src = f"lesson|{date}|{start_t}|{end_t}|{subject}|{room or ''}"
                events.append({
                    "date": date, "start_time": start_t, "end_time": end_t,
                    "subject": subject, "room": room
                })
            except Exception:
                continue

        if offset < weeks - 1:
            new_sig = click_next_week_and_wait(driver, wait, current_sig)
            if not new_sig or new_sig == current_sig:
                break
            current_sig = new_sig

    return events

# ---------------------- endpoints (Security Removed) ----------------------

class FetchBody(BaseModel):
    class_name: str
    weeks: int = 1
    username: str
    password: str

@app.post("/fetch")
def fetch_post(body: FetchBody):
    driver = None
    try:
        driver = setup_driver()
        wait = WebDriverWait(driver, 20)

        # Log in with the credentials sent from the app
        login(driver, wait, username=body.username, password=body.password)

        events = extract_week_events_service(driver, wait, weeks=body.weeks, class_name_hint=body.class_name)
        return JSONResponse({"events": events})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    # 1. Get the IP first
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"

    current_ip = get_local_ip()
    port = int(os.getenv("PORT", "8000"))
    
    # 2. Print the info BEFORE starting the server
    print("-" * 50)
    print(f"ALARM APP BACKEND STARTING")
    print(f"Listening on: http://{current_ip}:{port}/fetch")
    print("-" * 50)

    # 3. NOW start the server (this line blocks everything below it)
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)