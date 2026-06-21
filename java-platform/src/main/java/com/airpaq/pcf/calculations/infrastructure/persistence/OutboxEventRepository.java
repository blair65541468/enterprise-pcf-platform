package com.airpaq.pcf.calculations.infrastructure.persistence;

import com.airpaq.pcf.calculations.domain.OutboxEvent;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface OutboxEventRepository extends JpaRepository<OutboxEvent, String> {
    @Query(
            value =
                    """
                    select * from outbox_event
                    where published_at is null
                    order by created_at
                    for update skip locked limit 50
                    """,
            nativeQuery = true)
    List<OutboxEvent> claimUnpublished();
}
