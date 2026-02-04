from datetime import date
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from app.services.clickhouse_service import execute_query, get_last_processed_date
from app.auth import get_current_user, TokenUser


router = APIRouter(prefix="/reports", tags=["reports"])


class ClientSummary(BaseModel):
    client_id: int
    client_external_id: str
    client_name: str
    client_email: str
    client_city: str
    client_country: str
    registration_date: date
    total_prostheses: int
    active_prostheses: int
    avg_daily_movements: Optional[float]
    avg_battery_level: Optional[float]
    avg_response_time_ms: Optional[float]
    total_errors_30d: int
    last_activity_date: Optional[date]
    days_since_last_service: Optional[int]


class TelemetryDaily(BaseModel):
    report_date: date
    client_id: int
    client_name: str
    prosthesis_serial_number: str
    prosthesis_model: str
    avg_battery_level: float
    min_battery_level: float
    max_battery_level: float
    avg_response_time_ms: float
    min_response_time_ms: int
    max_response_time_ms: int
    avg_grip_strength: float
    avg_myosignal_amplitude: float
    total_movements_count: int
    avg_temperature: float
    error_count: int
    records_count: int


class ClientReport(BaseModel):
    summary: ClientSummary
    telemetry_history: list[TelemetryDaily]
    data_available_until: Optional[date] = None


class ClientsListResponse(BaseModel):
    clients: list[ClientSummary]
    total: int


class DataAvailabilityResponse(BaseModel):
    last_processed_date: Optional[date]
    message: str


def get_effective_date_range(days: int) -> tuple[date, Optional[date]]:
    last_processed = get_last_processed_date()
    if last_processed is None:
        return (date.today(), None)
    
    from datetime import timedelta
    start_date = last_processed - timedelta(days=days)
    return (start_date, last_processed)


@router.get("/data-availability", response_model=DataAvailabilityResponse)
async def get_data_availability(
    current_user: TokenUser = Depends(get_current_user),
):
    last_processed = get_last_processed_date()
    if last_processed is None:
        return DataAvailabilityResponse(
            last_processed_date=None,
            message="No data has been processed yet"
        )
    return DataAvailabilityResponse(
        last_processed_date=last_processed,
        message=f"Data available up to {last_processed}"
    )


@router.get("/clients", response_model=ClientsListResponse)
async def get_clients_report(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: TokenUser = Depends(get_current_user),
):
    if not current_user.is_admin():
        raise HTTPException(
            status_code=403,
            detail="Access denied. Admin role required."
        )
    
    count_query = "SELECT count() as cnt FROM analytics.dm_client_summary FINAL"
    count_result = execute_query(count_query)
    total = count_result[0]["cnt"] if count_result else 0

    query = """
        SELECT 
            client_id,
            client_external_id,
            client_name,
            client_email,
            client_city,
            client_country,
            registration_date,
            total_prostheses,
            active_prostheses,
            avg_daily_movements,
            avg_battery_level,
            avg_response_time_ms,
            total_errors_30d,
            last_activity_date,
            days_since_last_service
        FROM analytics.dm_client_summary FINAL
        ORDER BY client_id
        LIMIT {limit:UInt32}
        OFFSET {offset:UInt32}
    """

    result = execute_query(query, {"limit": limit, "offset": offset})

    return ClientsListResponse(
        clients=[ClientSummary(**row) for row in result],
        total=total,
    )


@router.get("/client/{client_id}", response_model=ClientReport)
async def get_client_report(
    client_id: int,
    days: int = Query(default=30, ge=1, le=365),
    current_user: TokenUser = Depends(get_current_user),
):
    if not current_user.is_admin() and current_user.client_id != client_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You can only access your own reports."
        )
    
    last_processed = get_last_processed_date()
    
    summary_query = """
        SELECT 
            client_id,
            client_external_id,
            client_name,
            client_email,
            client_city,
            client_country,
            registration_date,
            total_prostheses,
            active_prostheses,
            avg_daily_movements,
            avg_battery_level,
            avg_response_time_ms,
            total_errors_30d,
            last_activity_date,
            days_since_last_service
        FROM analytics.dm_client_summary FINAL
        WHERE client_id = {client_id:Int32}
    """

    summary_result = execute_query(summary_query, {"client_id": client_id})

    if not summary_result:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    if last_processed:
        telemetry_query = """
            SELECT 
                report_date,
                client_id,
                client_name,
                prosthesis_serial_number,
                prosthesis_model,
                avg_battery_level,
                min_battery_level,
                max_battery_level,
                avg_response_time_ms,
                min_response_time_ms,
                max_response_time_ms,
                avg_grip_strength,
                avg_myosignal_amplitude,
                total_movements_count,
                avg_temperature,
                error_count,
                records_count
            FROM analytics.dm_client_telemetry_daily FINAL
            WHERE client_id = {client_id:Int32}
              AND report_date >= {last_processed:Date} - {days:UInt32}
              AND report_date <= {last_processed:Date}
            ORDER BY report_date DESC, prosthesis_serial_number
        """
        telemetry_result = execute_query(
            telemetry_query, {"client_id": client_id, "days": days, "last_processed": last_processed}
        )
    else:
        telemetry_result = []

    return ClientReport(
        summary=ClientSummary(**summary_result[0]),
        telemetry_history=[TelemetryDaily(**row) for row in telemetry_result],
        data_available_until=last_processed,
    )


@router.get("/prosthesis/{serial_number}", response_model=ClientReport)
async def get_prosthesis_report(
    serial_number: str,
    days: int = Query(default=30, ge=1, le=365),
    current_user: TokenUser = Depends(get_current_user),
):
    ownership_query = """
        SELECT client_id 
        FROM analytics.dm_client_telemetry_daily FINAL
        WHERE prosthesis_serial_number = {serial_number:String}
        LIMIT 1
    """
    ownership_result = execute_query(ownership_query, {"serial_number": serial_number})
    
    if not ownership_result:
        raise HTTPException(
            status_code=404, detail=f"Prosthesis {serial_number} not found"
        )
    
    prosthesis_client_id = ownership_result[0]["client_id"]
    
    if not current_user.is_admin() and current_user.client_id != prosthesis_client_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You can only access your own prosthesis data."
        )
    
    last_processed = get_last_processed_date()
    
    summary_query = """
        SELECT 
            client_id,
            client_external_id,
            client_name,
            client_email,
            client_city,
            client_country,
            registration_date,
            total_prostheses,
            active_prostheses,
            avg_daily_movements,
            avg_battery_level,
            avg_response_time_ms,
            total_errors_30d,
            last_activity_date,
            days_since_last_service
        FROM analytics.dm_client_summary FINAL
        WHERE client_id = {client_id:Int32}
    """
    summary_result = execute_query(summary_query, {"client_id": prosthesis_client_id})
    
    if not summary_result:
        raise HTTPException(status_code=404, detail="Client data not found")

    if last_processed:
        telemetry_query = """
            SELECT 
                report_date,
                client_id,
                client_name,
                prosthesis_serial_number,
                prosthesis_model,
                avg_battery_level,
                min_battery_level,
                max_battery_level,
                avg_response_time_ms,
                min_response_time_ms,
                max_response_time_ms,
                avg_grip_strength,
                avg_myosignal_amplitude,
                total_movements_count,
                avg_temperature,
                error_count,
                records_count
            FROM analytics.dm_client_telemetry_daily FINAL
            WHERE prosthesis_serial_number = {serial_number:String}
              AND report_date >= {last_processed:Date} - {days:UInt32}
              AND report_date <= {last_processed:Date}
            ORDER BY report_date DESC
        """
        telemetry_result = execute_query(
            telemetry_query, {"serial_number": serial_number, "days": days, "last_processed": last_processed}
        )
    else:
        telemetry_result = []

    return ClientReport(
        summary=ClientSummary(**summary_result[0]),
        telemetry_history=[TelemetryDaily(**row) for row in telemetry_result],
        data_available_until=last_processed,
    )


@router.get("/me", response_model=ClientReport)
async def get_my_report(
    days: int = Query(default=30, ge=1, le=365),
    current_user: TokenUser = Depends(get_current_user),
):
    if current_user.client_id is None:
        raise HTTPException(
            status_code=403, 
            detail="User does not have an associated client_id"
        )
    
    client_id = current_user.client_id
    last_processed = get_last_processed_date()
    
    summary_query = """
        SELECT 
            client_id,
            client_external_id,
            client_name,
            client_email,
            client_city,
            client_country,
            registration_date,
            total_prostheses,
            active_prostheses,
            avg_daily_movements,
            avg_battery_level,
            avg_response_time_ms,
            total_errors_30d,
            last_activity_date,
            days_since_last_service
        FROM analytics.dm_client_summary FINAL
        WHERE client_id = {client_id:Int32}
    """

    summary_result = execute_query(summary_query, {"client_id": client_id})

    if not summary_result:
        raise HTTPException(status_code=404, detail="Client data not found")

    if last_processed:
        telemetry_query = """
            SELECT 
                report_date,
                client_id,
                client_name,
                prosthesis_serial_number,
                prosthesis_model,
                avg_battery_level,
                min_battery_level,
                max_battery_level,
                avg_response_time_ms,
                min_response_time_ms,
                max_response_time_ms,
                avg_grip_strength,
                avg_myosignal_amplitude,
                total_movements_count,
                avg_temperature,
                error_count,
                records_count
            FROM analytics.dm_client_telemetry_daily FINAL
            WHERE client_id = {client_id:Int32}
              AND report_date >= {last_processed:Date} - {days:UInt32}
              AND report_date <= {last_processed:Date}
            ORDER BY report_date DESC, prosthesis_serial_number
        """
        telemetry_result = execute_query(
            telemetry_query, {"client_id": client_id, "days": days, "last_processed": last_processed}
        )
    else:
        telemetry_result = []

    return ClientReport(
        summary=ClientSummary(**summary_result[0]),
        telemetry_history=[TelemetryDaily(**row) for row in telemetry_result],
        data_available_until=last_processed,
    )
