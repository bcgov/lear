# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""The BN Retry service worker.

This module processes firms to check BN15 status.
"""

import uuid
from datetime import UTC, datetime

from flask import current_app
from simple_cloudevent import SimpleCloudEvent, to_queue_message
from sqlalchemy import func, or_

from bn_retry import db
from bn_retry.services import check_bn15_status_batch, gcp_queue
from business_model.models import Business


def get_businesses_to_process(limit: int = 20, skip: int = 0):
    """Get list of businesses that need BN15 retry."""
    try:
        bn15_length = 15
        businesses = (
            db.session.query(Business)
            .filter(
                Business.legal_type.in_(["SP", "GP"]),
                Business.identifier.not_like("FM0%"),  # FM0's are old, created in colin
                or_(Business.tax_id.is_(None), func.length(Business.tax_id) != bn15_length),
            )
            .order_by(Business.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

        current_app.logger.debug(f"Found {len(businesses)} businesses to process (limit={limit}, skip={skip})")
        return businesses
    except Exception as err:
        current_app.logger.error(f"Error querying businesses: {err}")
        raise


def update_business_bn(business: Business, bn15: str):
    """Update business tax_id with BN15."""
    try:
        business.tax_id = bn15
        db.session.add(business)
        db.session.commit()
        current_app.logger.debug(f"Updated business {business.identifier} with BN15: {bn15}")
    except Exception as err:
        db.session.rollback()
        current_app.logger.error(f"Error updating business {business.identifier}: {err}")
        raise


def publish_email_notification(identifier: str):
    """Publish email notification to BUSINESS_EMAILER_TOPIC."""
    try:
        ce = SimpleCloudEvent(
            id=str(uuid.uuid4()),
            source="bn-retry",
            subject="bn",
            time=datetime.now(UTC),
            type="bc.registry.business.bn",
            data={"email": {"type": "businessNumber", "option": "bn", "identifier": identifier}},
        )
        topic = current_app.config.get("BUSINESS_EMAILER_TOPIC")
        gcp_queue.publish(topic, to_queue_message(ce))
        current_app.logger.debug(f"Published email notification for {identifier}")
    except Exception as err:
        current_app.logger.error(f"Failed to publish email notification for {identifier}: {err}", exc_info=True)
        raise


def publish_business_event(identifier: str):
    """Publish business change event to BUSINESS_EVENTS_TOPIC."""
    try:
        ce = SimpleCloudEvent(
            id=str(uuid.uuid4()),
            source="bn-retry",
            subject="bn",
            time=datetime.now(UTC),
            type="bc.registry.business.bn",
            data={"identifier": identifier},
        )
        topic = current_app.config.get("BUSINESS_EVENTS_TOPIC")
        gcp_queue.publish(topic, to_queue_message(ce))
        current_app.logger.debug(f"Published business event for {identifier}")
    except Exception as err:
        current_app.logger.error(f"Failed to publish business event for {identifier}: {err}", exc_info=True)
        raise


def run_job():
    """Run the BN15 retry job with batch processing.

    Workflow:
    1. Loop until no more businesses found:
        a. Query up to 20 businesses with identifiers not starting with 'FM0' that don't have a valid BN15
        b. Collect identifiers and batch check against Colin API.
        c. For matches, update LEAR, send email, and publish event.
        d. Commit changes.
    """
    try:
        current_app.logger.info("Starting BN retry job")

        batch_size = current_app.config.get("BATCH_SIZE")
        skip_count = 0
        total_processed = 0
        total_updated = 0

        while True:
            # 1. Get batch of businesses
            businesses = get_businesses_to_process(limit=batch_size, skip=skip_count)

            if not businesses:
                break

            total_processed += len(businesses)

            # Map identifier -> Business object
            business_map = {b.identifier: b for b in businesses}
            identifiers = list(business_map.keys())

            # 2. Batch check BN15
            current_app.logger.info(f"Checking BN15 for batch of {len(identifiers)}: {identifiers}")
            bn_results = check_bn15_status_batch(identifiers)

            # 3. Process matches
            for result in bn_results:
                for identifier, bn15 in result.items():
                    business = business_map.get(identifier)
                    if not business:
                        continue

                    try:
                        update_business_bn(business, bn15)
                        publish_email_notification(identifier)
                        publish_business_event(identifier)
                    except Exception as ex:
                        current_app.logger.error(f"Error updating {identifier}: {ex}")
                        # Continue with other updates in batch

            # Log batch completion
            try:
                updates_count = len(bn_results)
                total_updated += updates_count
                current_app.logger.info(f"Batch complete. Updated {updates_count} businesses.")
            except Exception as ex:
                current_app.logger.error(f"Error in batch logging/tracking: {ex}")

            # Logic for next loop
            if updates_count < len(businesses):
                unprocessed_count = len(businesses) - updates_count
                skip_count += unprocessed_count
                current_app.logger.info(
                    f"Skipping {unprocessed_count} businesses in next batch (Total skip: {skip_count})"
                )
            else:
                pass

        current_app.logger.info(f"BN retry job completed. Reviewed: {total_processed}, Updated: {total_updated}")
    except Exception as err:
        current_app.logger.error(f"BN retry job failed: {err}")
        raise
