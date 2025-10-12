#!/usr/bin/env python3
"""
Comprehensive GitHub Stats Generator
Generates detailed statistics including private repos, forks, and organization work
"""

import os
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import base64

class GitHubStatsGenerator:
    def __init__(self, token, username):
        self.token = token
        self.username = username
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_all_repos(self):
        """Get all repositories including private, forks, and organization repos"""
        repos = []
        page = 1
        
        # Get user repos (including private)
        while True:
            url = f'https://api.github.com/user/repos?per_page=100&page={page}&type=all&sort=updated'
            response = self.session.get(url)
            if response.status_code != 200:
                break
            data = response.json()
            if not data:
                break
            repos.extend(data)
            page += 1
            
        # Get organization repos
        orgs_url = 'https://api.github.com/user/orgs'
        orgs_response = self.session.get(orgs_url)
        if orgs_response.status_code == 200:
            orgs = orgs_response.json()
            for org in orgs:
                org_name = org['login']
                page = 1
                while True:
                    url = f'https://api.github.com/orgs/{org_name}/repos?per_page=100&page={page}&type=all'
                    response = self.session.get(url)
                    if response.status_code != 200:
                        break
                    data = response.json()
                    if not data:
                        break
                    repos.extend(data)
                    page += 1
                    
        return repos
    
    def get_commit_stats(self, repo_full_name):
        """Get commit statistics for a repository"""
        stats = {
            'commits': 0,
            'additions': 0,
            'deletions': 0,
            'changed_files': 0
        }
        
        # Get commits from the user
        try:
            url = f'https://api.github.com/repos/{repo_full_name}/commits?author={self.username}&per_page=100'
            response = self.session.get(url)
            if response.status_code != 200:
                return stats
                
            commits = response.json()
            stats['commits'] = len(commits)
            
            # Get detailed stats for recent commits (API rate limit consideration)
            for commit in commits[:50]:  # Limit to avoid rate limits
                commit_url = f'https://api.github.com/repos/{repo_full_name}/commits/{commit["sha"]}'
                commit_response = self.session.get(commit_url)
                if commit_response.status_code == 200:
                    commit_data = commit_response.json()
                    if 'stats' in commit_data:
                        stats['additions'] += commit_data['stats'].get('additions', 0)
                        stats['deletions'] += commit_data['stats'].get('deletions', 0)
                        if 'files' in commit_data:
                            stats['changed_files'] += len(commit_data['files'])
                            
        except Exception as e:
            print(f"Error getting commit stats for {repo_full_name}: {e}")
            
        return stats
    
    def get_language_stats(self, repo_full_name):
        """Get language statistics for a repository"""
        try:
            url = f'https://api.github.com/repos/{repo_full_name}/languages'
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting language stats for {repo_full_name}: {e}")
        return {}
    
    def generate_comprehensive_stats(self):
        """Generate comprehensive statistics"""
        print("Fetching all repositories...")
        repos = self.get_all_repos()
        
        total_stats = {
            'repositories': {
                'total': len(repos),
                'public': 0,
                'private': 0,
                'forks': 0,
                'original': 0,
                'organization': 0
            },
            'commits': {
                'total': 0,
                'additions': 0,
                'deletions': 0,
                'changed_files': 0
            },
            'languages': defaultdict(int),
            'organizations': set(),
            'repositories_by_org': defaultdict(list)
        }
        
        for repo in repos:
            # Repository categorization
            if repo['private']:
                total_stats['repositories']['private'] += 1
            else:
                total_stats['repositories']['public'] += 1
                
            if repo['fork']:
                total_stats['repositories']['forks'] += 1
            else:
                total_stats['repositories']['original'] += 1
                
            if repo['owner']['login'] != self.username:
                total_stats['repositories']['organization'] += 1
                total_stats['organizations'].add(repo['owner']['login'])
                total_stats['repositories_by_org'][repo['owner']['login']].append(repo['name'])
            
            print(f"Processing {repo['full_name']}...")
            
            # Get commit stats
            commit_stats = self.get_commit_stats(repo['full_name'])
            total_stats['commits']['total'] += commit_stats['commits']
            total_stats['commits']['additions'] += commit_stats['additions']
            total_stats['commits']['deletions'] += commit_stats['deletions']
            total_stats['commits']['changed_files'] += commit_stats['changed_files']
            
            # Get language stats
            languages = self.get_language_stats(repo['full_name'])
            for lang, bytes_count in languages.items():
                total_stats['languages'][lang] += bytes_count
        
        # Convert organizations set to list for JSON serialization
        total_stats['organizations'] = list(total_stats['organizations'])
        total_stats['repositories_by_org'] = dict(total_stats['repositories_by_org'])
        
        return total_stats
    
    def generate_markdown_stats(self, stats):
        """Generate markdown representation of stats"""
        
        # Sort languages by usage
        sorted_languages = sorted(stats['languages'].items(), key=lambda x: x[1], reverse=True)
        total_bytes = sum(stats['languages'].values())
        
        markdown = f"""# Comprehensive GitHub Statistics

## 📊 Repository Overview
- **Total Repositories**: {stats['repositories']['total']}
- **Public**: {stats['repositories']['public']}
- **Private**: {stats['repositories']['private']}  
- **Original**: {stats['repositories']['original']}
- **Forks**: {stats['repositories']['forks']}
- **Organization Repos**: {stats['repositories']['organization']}

## 💻 Commit Activity  
- **Total Commits**: {stats['commits']['total']:,}
- **Lines Added**: {stats['commits']['additions']:,}
- **Lines Deleted**: {stats['commits']['deletions']:,}
- **Files Changed**: {stats['commits']['changed_files']:,}
- **Net Lines**: {stats['commits']['additions'] - stats['commits']['deletions']:,}

## 🚀 Organizations
{chr(10).join([f"- **{org}**: {len(repos)} repositories" for org, repos in stats['repositories_by_org'].items()])}

## 📈 Language Breakdown
"""
        
        for i, (lang, bytes_count) in enumerate(sorted_languages[:10]):
            percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
            markdown += f"- **{lang}**: {percentage:.1f}% ({bytes_count:,} bytes)\n"
            
        markdown += f"""
## 🎯 Key Statistics
- **Average commits per repo**: {stats['commits']['total'] / max(stats['repositories']['total'], 1):.1f}
- **Most used language**: {sorted_languages[0][0] if sorted_languages else 'N/A'}
- **Code efficiency**: {stats['commits']['additions'] / max(stats['commits']['total'], 1):.1f} lines per commit
- **Active organizations**: {len(stats['organizations'])}

---
*Last updated: {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}*
*Generated with comprehensive GitHub API analysis including private repositories and organization work*
"""
        
        return markdown

def main():
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("Please set GITHUB_TOKEN environment variable")
        return
        
    username = 'OliverPerring'
    
    generator = GitHubStatsGenerator(token, username)
    
    print("Generating comprehensive GitHub statistics...")
    stats = generator.generate_comprehensive_stats()
    
    # Save JSON stats
    with open('assets/comprehensive-stats.json', 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    # Generate and save markdown
    markdown = generator.generate_markdown_stats(stats)
    with open('assets/comprehensive-stats.md', 'w') as f:
        f.write(markdown)
    
    print("Stats generated successfully!")
    print(f"Total commits: {stats['commits']['total']}")
    print(f"Total repositories: {stats['repositories']['total']}")
    print(f"Organizations: {', '.join(stats['organizations'])}")

if __name__ == "__main__":
    main()