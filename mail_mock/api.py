"""REST API for programmatic access to captured emails."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from .storage import EmailStorage


def create_api_blueprint(storage: EmailStorage) -> Blueprint:
    """Create Flask Blueprint with REST API routes."""
    api = Blueprint("api", __name__, url_prefix="/api")

    @api.route("/emails", methods=["GET"])
    def list_emails():
        """GET /api/emails - List captured emails.

        Query params:
            limit: Max results (default 100)
            offset: Pagination offset (default 0)
            search: Search term for subject/sender/body
        """
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        search = request.args.get("search", None, type=str)

        emails = storage.list_all(limit=limit, offset=offset, search=search)
        total = storage.count()

        return jsonify({
            "emails": [e.to_dict() for e in emails],
            "total": total,
            "limit": limit,
            "offset": offset,
        })

    @api.route("/emails/<int:email_id>", methods=["GET"])
    def get_email(email_id: int):
        """GET /api/emails/<id> - Get full email details."""
        em = storage.get(email_id)
        if em is None:
            return jsonify({"error": "Email not found"}), 404
        return jsonify(em.to_dict())

    @api.route("/emails/<int:email_id>", methods=["DELETE"])
    def delete_email(email_id: int):
        """DELETE /api/emails/<id> - Delete a specific email."""
        if storage.delete(email_id):
            return jsonify({"deleted": True, "id": email_id})
        return jsonify({"error": "Email not found"}), 404

    @api.route("/emails", methods=["DELETE"])
    def clear_emails():
        """DELETE /api/emails - Clear all captured emails."""
        count = storage.clear()
        return jsonify({"deleted": True, "count": count})

    @api.route("/stats", methods=["GET"])
    def stats():
        """GET /api/stats - Get server statistics."""
        return jsonify({
            "total_emails": storage.count(),
        })

    return api
