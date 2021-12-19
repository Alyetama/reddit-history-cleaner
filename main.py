#!/usr/bin/env python
# coding: utf-8

import os
import time
import shutil
import signal
import sys
from getpass import getpass

from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm


def keyboard_interrupt_handler(sig, frame):
    logger.info(f'KeyboardInterrupt exception has been caught...')
    try:
        driver.quit()
        logger.info('Terminated chromedriver gracefully...')
    except NameError:
        pass
    sys.exit(0)


def debugger(msg):
    if debug:  # global
        logger.exception(msg)


def main(disable_headless=False, debug=False):
    username = input('Username: ')
    passwd = getpass()

    signal.signal(signal.SIGINT, keyboard_interrupt_handler)

    while True:
        try:
            selected_option = int(
                input(
                    'Remove:\n  1. Comments only\n  2. Posts only\n  3. Comments and posts\nChoice: '
                ))
            break
        except ValueError:
            logger.warning('Enter numerical values only (1, 2, or 3)!')

    elements_to_remove = ['comments', 'submitted']
    if selected_option != 3:
        elements_to_remove = [elements_to_remove[selected_option - 1]]

    logger.info('Initializing...')

    driver_path = shutil.which('chromedriver')
    if not driver_path:
        driver_path = input(
            '⚠️ Can\'t find `chromedriver` in $PATH! Enter it manually: ')
    service = Service(driver_path)
    options = webdriver.ChromeOptions()
    if not disable_headless:
        options.add_argument('headless')
    driver = webdriver.Chrome(options=options, service=service)
    driver.get(f'https://old.reddit.com/user/{username}/')

    for e in driver.find_elements(By.TAG_NAME, 'input'):
        if e.get_attribute('name') == 'user':
            time.sleep(0.5)
            e.send_keys(username)
        elif e.get_attribute('name') == 'passwd':
            e.send_keys(passwd)
            time.sleep(0.5)
            driver.find_element(By.CLASS_NAME, 'submit').click()
            break

    time.sleep(5)
    logger.info('Started...')

    for page in elements_to_remove:
        page_url = f'https://old.reddit.com/user/{username}/{page}/'
        driver.get(page_url)
        time.sleep(3)

        n = 0
        e = 0
        while True:
            driver.refresh()
            try:
                assert driver.current_url == page_url
            except AssertionError as err:
                debugger(err)
                logger.error(
                    f'AssertionError: The current page URL does not match the task!'
                )
                break
            entries = driver.find_element(By.ID, 'siteTable').find_elements(
                By.CLASS_NAME, 'thing')
            if not entries:
                break
            for entry in tqdm(entries, desc='Running checks'):
                try:
                    el = WebDriverWait(entry, 2).until(
                        ec.presence_of_element_located(
                            (By.CLASS_NAME, 'del-button')))
                    el.click()
                    time.sleep(0.5)
                    WebDriverWait(el, 2).until(
                        ec.element_to_be_clickable(
                            (By.CLASS_NAME, 'yes'))).click()
                    n += 1
                    e = 0
                except (ElementClickInterceptedException,
                        ElementNotInteractableException,
                        StaleElementReferenceException,
                        TimeoutException) as exc:
                    debugger(exc)
                    try:
                        e += 1
                    except UnboundLocalError as exc:
                        debugger(exc)
                        e = 1
                    if e > 50:
                        logger.error(
                            'Something is not right...\nRun again with `--disable-headless` flag.'
                        )
                        logger.info('Terminating...')
                        driver.quit()
                        sys.exit(1)

                    logger.warning(
                        f'⚠️ Failed to remove an item... but will try again...'
                    )

        logger.info(
            f'✅ Done!\n🗑️ Removed {n} {page.replace("submitted", "posts")[:-1]}(s).'
        )
    driver.quit()


if __name__ == '__main__':
    logger.add('reddit_cleaner.log')
    logger.info(f'Saving logs to {os.getcwd()}/reddit_cleaner.log')
    disable_headless = False
    debug = False
    if len(sys.argv) > 1:
        if '--disable-headless' in sys.argv:
            disable_headless = True
        if '--debug' in sys.argv:
            debug = True
    logger.info(f'Headless mode is disabled: {disable_headless}')
    logger.info(f'Debugging mode: {debug}')

    main(disable_headless=disable_headless, debug=debug)
