#!/usr/bin/env python3
"""
Health Check Module for Spotify Voice Assistant
Verifies all dependencies, configurations, and system requirements.

Usage: python -m app.health_check
"""

import os
import sys
import json
import logging
import subprocess
from typing import Dict, List, Tuple, Any


class HealthCheck:
    """Comprehensive health check for the Spotify Voice Assistant."""
    
    def __init__(self):
        self.results = {
            'passed': [],
            'warnings': [],
            'failed': [],
            'info': []
        }
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for health check."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def check_python_version(self) -> bool:
        """Check if Python version is compatible."""
        version = sys.version_info
        if version >= (3, 7):
            self.results['passed'].append(f"✅ Python {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            self.results['failed'].append(f"❌ Python {version.major}.{version.minor}.{version.micro} (requires >= 3.7)")
            return False

    def check_python_packages(self) -> bool:
        """Check if required Python packages are installed."""
        required_packages = [
            'spotipy',
            'speech_recognition', 
            'pyttsx3',
            'requests'
        ]
        
        optional_packages = [
            'cryptography',  # For secure token storage
            'win10toast',    # Windows notifications
            'plyer'          # Cross-platform notifications
        ]
        
        all_good = True
        
        for package in required_packages:
            try:
                __import__(package)
                self.results['passed'].append(f"✅ {package} installed")
            except ImportError:
                self.results['failed'].append(f"❌ {package} not installed (required)")
                all_good = False
        
        for package in optional_packages:
            try:
                __import__(package)
                self.results['passed'].append(f"✅ {package} installed (optional)")
            except ImportError:
                self.results['warnings'].append(f"⚠️ {package} not installed (optional)")
        
        return all_good

    def check_environment_variables(self) -> bool:
        """Check if required environment variables are set."""
        required_vars = [
            'SPOTIFY_CLIENT_ID',
            'SPOTIFY_CLIENT_SECRET'
        ]
        
        optional_vars = [
            'SPOTIFY_REDIRECT_URI',
            'WAKE_WORD'
        ]
        
        all_good = True
        
        for var in required_vars:
            value = os.getenv(var)
            if value and value.strip():
                self.results['passed'].append(f"✅ {var} is set")
            else:
                self.results['failed'].append(f"❌ {var} not set (required)")
                all_good = False
        
        for var in optional_vars:
            value = os.getenv(var)
            if value and value.strip():
                self.results['passed'].append(f"✅ {var} is set")
            else:
                self.results['info'].append(f"ℹ️ {var} not set (using default)")
        
        return all_good

    def check_audio_system(self) -> bool:
        """Check if audio system is working."""
        try:
            import speech_recognition as sr
            
            # Check microphone availability
            mic_names = sr.Microphone.list_microphone_names()
            if mic_names:
                self.results['passed'].append(f"✅ Found {len(mic_names)} microphone(s)")
                self.results['info'].append(f"ℹ️ Default microphone: {mic_names[0] if mic_names else 'None'}")
            else:
                self.results['warnings'].append("⚠️ No microphones detected")
            
            # Test TTS
            try:
                import pyttsx3
                tts = pyttsx3.init()
                self.results['passed'].append("✅ Text-to-Speech system available")
                tts.stop()
            except Exception as e:
                self.results['warnings'].append(f"⚠️ TTS system error: {e}")
            
            return True
            
        except ImportError as e:
            self.results['failed'].append(f"❌ Audio system check failed: {e}")
            return False

    def check_spotify_connectivity(self) -> bool:
        """Check Spotify API connectivity (if credentials are available)."""
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        if not (client_id and client_secret):
            self.results['info'].append("ℹ️ Skipping Spotify connectivity check (credentials not set)")
            return True
        
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials
            
            # Test basic API connectivity using client credentials flow
            auth_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
            
            # Try a simple API call
            results = sp.search(q='test', type='track', limit=1)
            self.results['passed'].append("✅ Spotify API connectivity working")
            return True
            
        except Exception as e:
            self.results['failed'].append(f"❌ Spotify API connectivity failed: {e}")
            return False

    def check_platform_support(self) -> bool:
        """Check platform-specific features."""
        from .platform_utils import (
            get_platform, 
            is_windows, 
            is_linux, 
            is_mac,
            get_spotify_executable_path,
            get_notification_command
        )
        
        platform = get_platform()
        self.results['passed'].append(f"✅ Platform: {platform}")
        
        # Check Spotify executable
        spotify_path = get_spotify_executable_path()
        if spotify_path:
            self.results['passed'].append(f"✅ Spotify found: {spotify_path}")
        else:
            self.results['warnings'].append("⚠️ Spotify application not found")
        
        # Check notification system
        notif_cmd = get_notification_command()
        if notif_cmd:
            self.results['passed'].append(f"✅ Notification system: {notif_cmd}")
        else:
            self.results['info'].append("ℹ️ No native notification system (will use fallback)")
        
        return True

    def check_file_permissions(self) -> bool:
        """Check file system permissions for cache and logs."""
        directories_to_check = [
            ('cache', '../cache'),
            ('logs', '../logs'),
            ('calibration', '../calibration')
        ]
        
        all_good = True
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        for name, rel_path in directories_to_check:
            dir_path = os.path.join(base_dir, rel_path.lstrip('../'))
            
            try:
                # Create directory if it doesn't exist
                os.makedirs(dir_path, exist_ok=True)
                
                # Test write permissions
                test_file = os.path.join(dir_path, '.test_write')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                
                self.results['passed'].append(f"✅ {name} directory writable: {dir_path}")
                
            except Exception as e:
                self.results['failed'].append(f"❌ {name} directory not writable: {e}")
                all_good = False
        
        return all_good

    def check_network_connectivity(self) -> bool:
        """Check basic network connectivity to required services."""
        endpoints = [
            ('Google Speech API', 'speech.googleapis.com', 443),
            ('Spotify API', 'api.spotify.com', 443)
        ]
        
        all_good = True
        
        for name, host, port in endpoints:
            try:
                import socket
                sock = socket.create_connection((host, port), timeout=5)
                sock.close()
                self.results['passed'].append(f"✅ {name} connectivity")
            except Exception as e:
                self.results['warnings'].append(f"⚠️ {name} connectivity issues: {e}")
                # Don't mark as failed since network issues might be temporary
        
        return all_good

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return results."""
        print("🔍 Spotify Voice Assistant - Health Check")
        print("=" * 50)
        
        checks = [
            ("Python Version", self.check_python_version),
            ("Python Packages", self.check_python_packages),
            ("Environment Variables", self.check_environment_variables),
            ("Audio System", self.check_audio_system),
            ("Platform Support", self.check_platform_support),
            ("File Permissions", self.check_file_permissions),
            ("Network Connectivity", self.check_network_connectivity),
            ("Spotify API", self.check_spotify_connectivity),
        ]
        
        results_summary = {
            'total_checks': len(checks),
            'passed_checks': 0,
            'failed_checks': 0,
            'overall_status': 'unknown'
        }
        
        for check_name, check_func in checks:
            print(f"\n🔍 Checking {check_name}...")
            try:
                success = check_func()
                if success:
                    results_summary['passed_checks'] += 1
                    print(f"✅ {check_name} - OK")
                else:
                    results_summary['failed_checks'] += 1
                    print(f"❌ {check_name} - FAILED")
            except Exception as e:
                results_summary['failed_checks'] += 1
                self.results['failed'].append(f"❌ {check_name} check crashed: {e}")
                print(f"💥 {check_name} - CRASHED: {e}")
        
        # Determine overall status
        if results_summary['failed_checks'] == 0:
            results_summary['overall_status'] = 'healthy'
        elif results_summary['failed_checks'] <= 2:
            results_summary['overall_status'] = 'warning'
        else:
            results_summary['overall_status'] = 'critical'
        
        # Display summary
        self.display_summary(results_summary)
        
        return {
            'summary': results_summary,
            'details': self.results
        }

    def display_summary(self, summary: Dict[str, Any]) -> None:
        """Display health check summary."""
        print("\n" + "=" * 50)
        print("📊 HEALTH CHECK SUMMARY")
        print("=" * 50)
        
        # Display results by category
        if self.results['passed']:
            print("\n✅ PASSED:")
            for item in self.results['passed']:
                print(f"   {item}")
        
        if self.results['warnings']:
            print("\n⚠️  WARNINGS:")
            for item in self.results['warnings']:
                print(f"   {item}")
        
        if self.results['failed']:
            print("\n❌ FAILED:")
            for item in self.results['failed']:
                print(f"   {item}")
        
        if self.results['info']:
            print("\nℹ️  INFO:")
            for item in self.results['info']:
                print(f"   {item}")
        
        # Overall status
        status_emoji = {
            'healthy': '🟢',
            'warning': '🟡', 
            'critical': '🔴'
        }
        
        print(f"\n{status_emoji.get(summary['overall_status'], '❓')} OVERALL STATUS: {summary['overall_status'].upper()}")
        print(f"📈 Checks: {summary['passed_checks']}/{summary['total_checks']} passed")
        
        # Recommendations
        if summary['overall_status'] == 'critical':
            print("\n🚨 CRITICAL ISSUES FOUND:")
            print("   Please fix failed checks before running the assistant.")
        elif summary['overall_status'] == 'warning':
            print("\n⚠️  SOME ISSUES FOUND:")
            print("   Assistant should work but may have limited functionality.")
        else:
            print("\n🎉 ALL SYSTEMS GO!")
            print("   Your Spotify Voice Assistant is ready to use!")


def main():
    """Main entry point for health check."""
    health_check = HealthCheck()
    results = health_check.run_all_checks()
    
    # Exit with appropriate code
    if results['summary']['overall_status'] == 'critical':
        sys.exit(1)
    elif results['summary']['overall_status'] == 'warning':
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()