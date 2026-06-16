-- ==========================================
-- 1. Vista: vw_resumen_clientes
-- Descripción: Muestra un resumen rápido de la cantidad de paquetes y el total de libras por cada cliente.
-- ==========================================
CREATE OR REPLACE VIEW vw_resumen_clientes AS
SELECT 
    c.id AS cliente_id,
    c.nombre_completo,
    c.cedula,
    COUNT(p.id) AS total_paquetes,
    COALESCE(SUM(p.peso), 0) AS libras_totales
FROM clientes c
LEFT JOIN paquetes p ON c.id = p.cliente_id
GROUP BY c.id, c.nombre_completo, c.cedula;

-- ==========================================
-- 2. Vista: vw_facturas_pendientes
-- Descripción: Muestra las facturas que no están pagadas, calculando lo abonado y el saldo pendiente.
-- ==========================================
CREATE OR REPLACE VIEW vw_facturas_pendientes AS
SELECT 
    f.id AS factura_id,
    f.numero AS numero_factura,
    c.nombre_completo AS cliente,
    f.estado,
    f.total AS total_facturado,
    COALESCE(SUM(pg.monto), 0) AS total_abonado,
    (f.total - COALESCE(SUM(pg.monto), 0)) AS saldo_pendiente,
    f.fecha_emision
FROM facturas f
JOIN clientes c ON f.cliente_id = c.id
LEFT JOIN pagos pg ON f.id = pg.factura_id
WHERE f.estado != 'pagada'
GROUP BY f.id, f.numero, c.nombre_completo, f.estado, f.total, f.fecha_emision;

-- ==========================================
-- 3. Vista: vw_auditoria_usuarios
-- Descripción: Muestra a los usuarios activos, su rol y cuántas actividades han registrado en el sistema.
-- ==========================================
CREATE OR REPLACE VIEW vw_auditoria_usuarios AS
SELECT 
    u.id AS usuario_id,
    u.username,
    u.nombre_completo,
    u.rol,
    u.activo,
    COUNT(ra.id) AS total_acciones_registradas
FROM usuarios u
LEFT JOIN registro_actividades ra ON u.id = ra.usuario_id
GROUP BY u.id, u.username, u.nombre_completo, u.rol, u.activo;
