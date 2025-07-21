"""
Blog routes for the YouTube Deep Summary application
Displays existing AI summaries formatted as blog posts
"""
from flask import Blueprint, render_template, request, jsonify, abort
from ..database_storage import database_storage
from ..utils.helpers import format_summary_html
import markdown

blog_bp = Blueprint('blog', __name__, url_prefix='/blog')


@blog_bp.route('/')
def blog_home():
    """Main blog listing page with infinite scroll"""
    try:
        # Get initial batch of blog posts (first 12)
        result = database_storage.get_blog_summaries_paginated(page=1, per_page=12)
        posts = result.get('posts', [])
        
        # Get total count from pagination info
        total_count = result.get('pagination', {}).get('total', 0)
        
        return render_template('blog/blog_home.html', 
                             initial_posts=posts,
                             total_count=total_count,
                             page_title="AI Video Blog")
    except Exception as e:
        print(f"Error loading blog home: {e}")
        return render_template('error.html', 
                             error="Failed to load blog posts"), 500


@blog_bp.route('/<channel_handle>')
def channel_blog(channel_handle):
    """Channel-specific blog listing page"""
    try:
        # Get channel info
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            abort(404)
        
        # Get initial batch of channel blog posts (first 12)
        result = database_storage.get_blog_summaries_by_channel_paginated(
            channel_handle, page=1, per_page=12
        )
        posts = result.get('posts', [])
        
        # Get total count from pagination info
        total_count = result.get('pagination', {}).get('total', 0)
        
        return render_template('blog/channel_blog.html',
                             initial_posts=posts,
                             channel_info=channel_info,
                             total_count=total_count,
                             page_title=f"{channel_info['channel_name']} - AI Video Blog")
    except Exception as e:
        print(f"Error loading channel blog for {channel_handle}: {e}")
        return render_template('error.html', 
                             error="Failed to load channel blog"), 500


@blog_bp.route('/<channel_handle>/<url_path>')
def blog_post(channel_handle, url_path):
    """Individual blog post page"""
    try:
        # Get the blog post data
        post = database_storage.get_blog_summary_by_slug(channel_handle, url_path)
        if not post:
            abort(404)
        
        # Format the summary content as HTML
        if post.get('summary_text'):
            # Convert markdown to HTML for proper formatting
            post['summary_html'] = markdown.markdown(
                post['summary_text'],
                extensions=['nl2br', 'fenced_code', 'tables', 'toc']
            )
        else:
            post['summary_html'] = "<p>No summary available for this video.</p>"
        
        # Get related posts from same channel (excluding current post)
        related_result = database_storage.get_blog_summaries_by_channel_paginated(
            channel_handle, page=1, per_page=6
        )
        related_posts = related_result.get('posts', [])
        # Filter out current post
        related_posts = [p for p in related_posts if p['video_id'] != post['video_id']][:4]
        
        return render_template('blog/blog_post.html',
                             post=post,
                             related_posts=related_posts,
                             page_title=post['title'])
    except Exception as e:
        print(f"Error loading blog post {channel_handle}/{url_path}: {e}")
        return render_template('error.html', 
                             error="Blog post not found"), 404


# API Endpoints for infinite scroll pagination

@blog_bp.route('/api/posts')
def api_blog_posts():
    """API endpoint for infinite scroll - all posts"""
    try:
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 12, type=int)
        
        # Limit the maximum items per request
        limit = min(limit, 24)
        
        # Convert offset/limit to page/per_page
        page = (offset // limit) + 1
        
        result = database_storage.get_blog_summaries_paginated(page=page, per_page=limit)
        posts = result.get('posts', [])
        
        return jsonify({
            'success': True,
            'posts': posts,
            'has_more': result.get('pagination', {}).get('has_next', False)
        })
    except Exception as e:
        print(f"Error loading blog posts API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@blog_bp.route('/api/posts/<channel_handle>')
def api_channel_blog_posts(channel_handle):
    """API endpoint for infinite scroll - channel-specific posts"""
    try:
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 12, type=int)
        
        # Limit the maximum items per request
        limit = min(limit, 24)
        
        # Convert offset/limit to page/per_page
        page = (offset // limit) + 1
        
        result = database_storage.get_blog_summaries_by_channel_paginated(
            channel_handle, page=page, per_page=limit
        )
        posts = result.get('posts', [])
        
        return jsonify({
            'success': True,
            'posts': posts,
            'has_more': result.get('pagination', {}).get('has_next', False)
        })
    except Exception as e:
        print(f"Error loading channel blog posts API for {channel_handle}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@blog_bp.route('/api/stats')
def api_blog_stats():
    """API endpoint for blog statistics"""
    try:
        # Get basic statistics
        result = database_storage.get_blog_summaries_paginated(page=1, per_page=1000)
        all_posts = result.get('posts', [])
        
        # Count unique channels
        unique_channels = set(post['channel_handle'] for post in all_posts if post.get('channel_handle'))
        
        stats = {
            'total_posts': len(all_posts),
            'total_channels': len(unique_channels),
            'latest_post_date': all_posts[0]['published_at'][:10] if all_posts else None
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        print(f"Error loading blog stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500