"""Web dashboard (Flask): inbox view, email reader, search."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from .storage import EmailStorage

TEMPLATE_DIR = Path(__file__).parent / "templates"


def create_app(storage: EmailStorage) -> Flask:
    """Create the Flask dashboard app.

    Args:
        storage: EmailStorage instance.

    Returns:
        Flask app.
    """
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
    )
    app.config["storage"] = storage

    @app.route("/")
    def inbox():
        """Render the inbox page."""
        search = request.args.get("q", "")
        page = int(request.args.get("page", 1))
        per_page = 50
        offset = (page - 1) * per_page

        emails = storage.list_all(limit=per_page, offset=offset, search=search or None)
        total = storage.count()

        return render_template(
            "inbox.html",
            emails=emails,
            search=search,
            page=page,
            total=total,
            per_page=per_page,
        )

    @app.route("/api/emails")
    def api_list():
        """JSON API: list emails."""
        search = request.args.get("q")
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        emails = storage.list_all(limit=limit, offset=offset, search=search)
        return jsonify({
            "emails": [e.to_dict() for e in emails],
            "total": storage.count(),
        })

    @app.route("/api/emails/<int:email_id>")
    def api_get(email_id: int):
        """JSON API: get single email."""
        em = storage.get(email_id)
        if not em:
            return jsonify({"error": "Not found"}), 404
        return jsonify(em.to_dict())

    @app.route("/api/emails/<int:email_id>/html")
    def api_html(email_id: int):
        """Render email HTML body in an iframe."""
        em = storage.get(email_id)
        if not em:
            return "Not found", 404
        if em.html_body:
            return Response(em.html_body, mimetype="text/html")
        return Response(f"<pre>{em.text_body}</pre>", mimetype="text/html")

    @app.route("/api/emails/<int:email_id>/raw")
    def api_raw(email_id: int):
        """Return raw email source."""
        em = storage.get(email_id)
        if not em:
            return "Not found", 404
        return Response(em.raw_data, mimetype="text/plain")

    @app.route("/api/emails/<int:email_id>", methods=["DELETE"])
    def api_delete(email_id: int):
        """Delete a single email."""
        if storage.delete(email_id):
            return jsonify({"deleted": True})
        return jsonify({"error": "Not found"}), 404

    @app.route("/api/emails", methods=["DELETE"])
    def api_clear():
        """Clear all emails."""
        count = storage.clear()
        return jsonify({"deleted": count})

    return app
