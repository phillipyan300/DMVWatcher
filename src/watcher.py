"""Core DMV appointment monitoring logic."""

import json
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from playwright.sync_api import Page, sync_playwright, TimeoutError as PlaywrightTimeoutError

from .notifications import NotificationService

logger = logging.getLogger(__name__)


class DMVWatcher:
    """Monitor DMV appointment availability for specified locations."""
    
    def __init__(self, targets: List[str], url: str, polling_interval: int = 300, 
                 max_date: Optional[str] = None, notification_service: Optional[NotificationService] = None):
        """
        Initialize DMVWatcher.
        
        Args:
            targets: List of county names to monitor (e.g., ['Mercer', 'Camden'])
            url: URL of the appointment booking page
            polling_interval: Seconds between checks (default: 300 = 5 minutes)
            max_date: Maximum date for appointments (format: "MM/DD/YYYY" or "YYYY-MM-DD")
                      Only alert if next available appointment is before this date
            notification_service: NotificationService instance for sending alerts
        """
        self.targets = [target.capitalize() for target in targets]  # Normalize to title case
        self.url = url
        self.polling_interval = polling_interval
        self.status_file = Path("status.json")
        self.last_status = self.load_status()
        self.notification_service = notification_service or NotificationService()
        self.first_check = True  # Track if this is the first check (to notify on startup if available)
        
        # Parse max_date if provided
        self.max_date = None
        if max_date:
            try:
                # Try MM/DD/YYYY format first
                if '/' in max_date:
                    self.max_date = datetime.strptime(max_date, "%m/%d/%Y").date()
                else:
                    # Try YYYY-MM-DD format
                    self.max_date = datetime.strptime(max_date, "%Y-%m-%d").date()
                logger.info(f"Date filter: Only alerting for appointments before {self.max_date}")
            except ValueError as e:
                logger.warning(f"Invalid date format '{max_date}': {e}. Date filtering disabled.")
        
    def load_status(self) -> Dict:
        """Load last known status from file."""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load status file: {e}")
        return {}
    
    def save_status(self, status: Dict):
        """Save current status to file."""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except IOError as e:
            logger.error(f"Could not save status file: {e}")
    
    def find_location_cards(self, page: Page) -> List[Dict]:
        """
        Find all location cards on the page.
        
        Returns:
            List of location info dicts with: name, county, status_text, has_button
        """
        locations = []
        
        try:
            # Wait for locations to load
            page.wait_for_selector('#locationsDiv', timeout=10000)
            
            # Get all location card containers
            cards = page.query_selector_all('.locationCardContainer')
            
            for card in cards:
                try:
                    # Get the header with location name
                    header = card.query_selector('.AppointcardHeader')
                    if not header:
                        continue
                    
                    location_text = header.inner_text().strip()
                    # Extract county name (first word before space or parenthesis)
                    county = location_text.split()[0] if location_text else ""
                    county_normalized = county.capitalize() if county else ""
                    
                    # Get status div (id starts with 'dateText')
                    status_div = card.query_selector('div[id^="dateText"]')
                    status_text = status_div.inner_text().strip() if status_div else "Unknown"
                    
                    # Debug: Also get raw HTML to see what's actually there
                    status_html = status_div.inner_html() if status_div else "No status div found"
                    
                    # Check for Make Appointment button
                    button = card.query_selector('a[id^="makebtn"]')
                    has_button = button is not None
                    
                    # Debug logging for raw data
                    if county_normalized in self.targets:  # Only log for target locations
                        logger.debug(f"Location: {location_text}")
                        logger.debug(f"Status HTML (raw): {repr(status_html)}")
                        logger.debug(f"Status text (inner_text): {repr(status_text)}")
                        logger.debug(f"Has button: {has_button}")
                    
                    # Button is the source of truth: if button exists, appointments are available
                    # The button only appears when appointments are actually available
                    is_available = has_button
                    
                    locations.append({
                        'name': location_text,
                        'county': county,
                        'status_text': status_text,
                        'has_button': has_button,
                        'is_available': is_available
                    })
                    
                except Exception as e:
                    logger.debug(f"Error parsing location card: {e}")
                    continue
                    
        except PlaywrightTimeoutError:
            logger.error("Timeout waiting for locations to load")
        except Exception as e:
            logger.error(f"Error finding location cards: {e}")
        
        return locations
    
    def check_target_locations(self, page: Page) -> Dict[str, Dict]:
        """
        Check status of target locations.
        
        Returns:
            Dict mapping county name to location info
        """
        all_locations = self.find_location_cards(page)
        target_status = {}
        
        for location in all_locations:
            county = location['county']
            # Normalize county name to title case for comparison (case-insensitive matching)
            county_normalized = county.capitalize() if county else ""
            if county_normalized in self.targets:
                # Debug: Log what we found
                logger.debug(f"Found {county_normalized} location:")
                logger.debug(f"  Name: {location['name']}")
                logger.debug(f"  Status text (raw): {repr(location['status_text'])}")
                logger.debug(f"  Has button: {location['has_button']}")
                logger.debug(f"  Is available (detected): {location['is_available']}")
                
                # Use normalized county name as key for consistency
                # If multiple locations for same county, keep the one with availability or first one
                if county_normalized not in target_status or location['is_available']:
                    target_status[county_normalized] = location
        
        return target_status
    
    def extract_appointment_info(self, status_text: str) -> Dict:
        """Extract appointment count and next available date from status text."""
        info = {
            'count': None,
            'next_available': None,
            'next_available_date': None  # Parsed datetime object
        }
        
        logger.debug(f"Parsing status text: {repr(status_text)}")
        
        # Early return if no appointments available - don't try to parse
        if 'No Appointments Available' in status_text:
            logger.debug("No appointments available - skipping parsing")
            return info
        
        # Only parse if appointments are actually available
        if 'Appointments Available' in status_text:
            try:
                # Extract count: "198 Appointments Available"
                parts = status_text.split('Appointments Available')
                logger.debug(f"Split parts: {parts}")
                if parts:
                    count_str = parts[0].strip()
                    logger.debug(f"Count string: {repr(count_str)}")
                    info['count'] = int(count_str)
                
                # Extract next available: "Next Available: 01/20/2026 11:45 AM"
                if 'Next Available:' in status_text:
                    next_part = status_text.split('Next Available:')[1].strip()
                    logger.debug(f"Next available part: {repr(next_part)}")
                    next_available_str = next_part.split('\n')[0].strip()
                    info['next_available'] = next_available_str
                    
                    # Parse the date: "01/20/2026 11:45 AM"
                    try:
                        # Try parsing with time: "MM/DD/YYYY HH:MM AM/PM"
                        info['next_available_date'] = datetime.strptime(next_available_str, "%m/%d/%Y %I:%M %p").date()
                    except ValueError:
                        try:
                            # Try parsing without time: "MM/DD/YYYY"
                            info['next_available_date'] = datetime.strptime(next_available_str.split()[0], "%m/%d/%Y").date()
                        except ValueError:
                            logger.warning(f"Could not parse date from '{next_available_str}'")
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse appointment info from '{status_text}': {e}")
        else:
            logger.debug("Status text does not contain 'Appointments Available'")
        
        return info
    
    def check_availability(self) -> Dict[str, Dict]:
        """
        Check current availability status for all targets.
        
        Creates a fresh browser session each time to ensure no caching issues.
        Uses incognito context and cache-busting to guarantee fresh data.
        
        Returns:
            Dict mapping county to current status info
        """
        with sync_playwright() as p:
            # Launch browser - each launch is completely fresh
            browser = p.chromium.launch(headless=True)
            # Create new context (fresh session, no cookies/cache from previous runs)
            # Each context is isolated - like incognito mode
            context = browser.new_context(
                ignore_https_errors=False,
                viewport={'width': 1280, 'height': 720}
            )
            # Create new page in fresh context
            page = context.new_page()
            
            # Set cache control headers to bypass any caching
            page.set_extra_http_headers({
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            })
            
            try:
                # Add cache-busting query parameter to URL
                cache_buster = f"?_t={int(time.time())}&_r={random.randint(1000, 9999)}"
                url_with_buster = self.url + (cache_buster if '?' not in self.url else '&' + cache_buster.lstrip('?'))
                
                logger.info(f"Navigating to {self.url} (fresh session, cache-busted)")
                
                # Navigate with no cache
                page.goto(
                    url_with_buster,
                    wait_until='networkidle',
                    timeout=30000,
                    # Force reload, bypass cache
                    referer=None
                )
                
                # Wait for the locations container to be visible (ensures dynamic content loaded)
                page.wait_for_selector('#locationsDiv', state='visible', timeout=10000)
                
                # Additional wait for any JavaScript to finish updating the page
                # The page might load data via AJAX after initial load
                time.sleep(3)  # Increased from 2 to 3 seconds for dynamic content
                
                # Verify we can see location cards before parsing
                cards = page.query_selector_all('.locationCardContainer')
                if not cards:
                    logger.warning("No location cards found - page may not have loaded correctly")
                    # Try waiting a bit more
                    time.sleep(2)
                
                target_status = self.check_target_locations(page)
                
                context.close()
                browser.close()
                return target_status
                
            except Exception as e:
                logger.error(f"Error checking availability: {e}")
                try:
                    context.close()
                except Exception:
                    pass  # Ignore errors during cleanup
                try:
                    browser.close()
                except Exception:
                    pass  # Ignore errors during cleanup
                return {}
    
    def monitor(self, duration_minutes: Optional[int] = None):
        """
        Start monitoring loop.
        
        Args:
            duration_minutes: How long to monitor (None or 0 = indefinite)
        """
        logger.info(f"Starting DMVWatcher for targets: {', '.join(self.targets)}")
        logger.info(f"Polling interval: {self.polling_interval} seconds")
        logger.info("Anti-spam: After notification, will wait 1 hour before next check")
        
        if duration_minutes:
            end_time = datetime.now() + timedelta(minutes=duration_minutes)
            logger.info(f"Monitoring until: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            logger.info("Monitoring indefinitely (press Ctrl+C to stop)")
        
        # Track if we just sent a notification (to prevent spam)
        notification_sent = False
        wait_after_notification = 3600  # 1 hour in seconds
        
        try:
            while True:
                # Check if duration exceeded
                if duration_minutes and datetime.now() >= end_time:
                    logger.info("Monitoring duration reached. Stopping.")
                    break
                
                logger.info("Checking appointment availability...")
                current_status = self.check_availability()
                
                # Check for changes and new availability
                notification_sent_this_cycle = False
                for county, location_info in current_status.items():
                    last_info = self.last_status.get(county, {})
                    last_available = last_info.get('is_available', False)
                    current_available = location_info.get('is_available', False)
                    
                    # Extract appointment info once (used for both notification and logging)
                    appt_info = None
                    if current_available:
                        appt_info = self.extract_appointment_info(location_info['status_text'])
                    
                    # If available (newly available OR first check with availability), check date filter and notify
                    if current_available and (not last_available or self.first_check) and appt_info:
                        # Check date filter if set
                        should_notify = True
                        if self.max_date and appt_info.get('next_available_date'):
                            if appt_info['next_available_date'] > self.max_date:
                                should_notify = False
                                logger.info(
                                    f"⏭️  Skipping {county}: Next available ({appt_info['next_available_date']}) "
                                    f"is after target date ({self.max_date})"
                                )
                        
                        if should_notify:
                            logger.info(f"🎉 NEW AVAILABILITY DETECTED for {county}!")
                            self.notification_service.notify_availability(
                                county, location_info, self.url, appt_info
                            )
                            notification_sent_this_cycle = True
                            notification_sent = True
                    
                    # Log current status
                    if current_available and appt_info:
                        date_info = ""
                        if appt_info.get('next_available_date'):
                            date_info = f" (Date: {appt_info['next_available_date']})"
                            if self.max_date:
                                if appt_info['next_available_date'] <= self.max_date:
                                    date_info += " ✅ Within date filter"
                                else:
                                    date_info += f" ⏭️  After {self.max_date}"
                        logger.info(
                            f"{county}: {appt_info['count']} appointments available "
                            f"(Next: {appt_info['next_available']}){date_info}"
                        )
                    else:
                        logger.info(f"{county}: No appointments available")
                
                # Update saved status
                self.last_status = current_status
                self.save_status(current_status)
                
                # Mark that first check is done
                self.first_check = False
                
                # Determine wait time: 1 hour after notification, otherwise normal interval
                if notification_sent_this_cycle:
                    wait_time = wait_after_notification
                    logger.info(f"📱 Notification sent! Waiting {wait_time} seconds (1 hour) before next check to avoid spam...")
                elif notification_sent and any(loc.get('is_available', False) for loc in current_status.values()):
                    # Still have availability, but already notified - wait 1 hour
                    wait_time = wait_after_notification
                    logger.info(f"⏰ Appointments still available (already notified). Waiting {wait_time} seconds (1 hour) before next check...")
                else:
                    # No notification sent, or no availability - resume normal polling
                    wait_time = self.polling_interval
                    notification_sent = False  # Reset flag when no availability
                    logger.info(f"Waiting {wait_time} seconds before next check...")
                
                time.sleep(wait_time)
                
        except KeyboardInterrupt:
            logger.info("\nMonitoring stopped by user.")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)

