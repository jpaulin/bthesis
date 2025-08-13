; label_areas.lsp
; AutoLISP / Visual LISP script
; 
; SHOW AREAs as text - inside a CAD schematic
; 
; Places a centered area label (e.g. "2.45 m²") inside 
; every closed polyline on the current layer.

; --------------
; The label color is supplied by function `label-color` (change as you like).
; The insertion point is chosen to be visibly inside the polygon by sampling the polygon's "bbox"
; and picking the point with maximum distance to the polygon edges (an approximation of the pole of inaccessibility).
;
; Usage: load the file, then run command: LABELAREAS
;
;;; --- helper: label color function ---
(defun label-color ()
  ; Return an AutoCAD color number (0-256).
  ; Default: 7 (white in many backgrounds). Change this function to return your preferred color index.
  7
)

;;; --- geometry helpers ---
(defun pts-from-lwpoly (ent)
  ;; Extract list of 2D points from LWPOLYLINE or POLYLINE ENT (works for both LW and old polyline)
  (cond
    ((= (cdr (assoc 0 (entget ent))) "LWPOLYLINE")
     (mapcar 'cdr (vl-remove-if-not '(lambda (x) (= (car x) 10)) (entget ent))))
    ((= (cdr (assoc 0 (entget ent))) "POLYLINE")
     (let ((v (cdr (assoc -1 (entget ent)))) pts vertex)
       (setq vertex (entnext ent))
       (while (and vertex (/= (cdr (assoc 0 (entget vertex))) "SEQEND"))
         (setq pts (cons (cdr (assoc 10 (entget vertex))) pts))
         (setq vertex (entnext vertex)))
       (reverse pts)))
  )
)

(defun bbox-of-pts (pts)
  (let ((xs (mapcar 'car pts)) (ys (mapcar 'cadr pts)))
    (list (apply 'min xs) (apply 'min ys) (apply 'max xs) (apply 'max ys))
  )
)

(defun point-in-poly (pt poly)
  ; Ray-casting algorithm. pt = (x y); poly = list of (x y)
  (let ((x (car pt)) (y (cadr pt)) (inside nil) (j (1- (length poly))) i xi yi xj yj)
    (setq i 0)
    (while (< i (length poly))
      (setq xi (car (nth i poly)) yi (cadr (nth i poly)))
      (setq xj (car (nth j poly)) yj (cadr (nth j poly)))
      (if (and (not (= yi yj))
               (<= (min yi yj) y)
               (> (max yi yj) y))
        (progn
          (if (> (+ xi (/ (* (- y yi) (- xj xi)) (- yj yi))) x)
            (setq inside (not inside))
          )
        )
      )
      (setq j i) (setq i (1+ i))
    )
    inside
  )
)

(defun dist-point-seg (px py x1 y1 x2 y2)
  ; distance from point to segment
  (let* ((lx (- x2 x1)) (ly (- y2 y1))
         (l2 (+ (* lx lx) (* ly ly)))
         (t (if (<= l2 1e-12) 0 (/ (+ (* (- px x1) lx) (* (- py y1) ly)) l2)))
         (tclamped (if (< t 0) 0 (if (> t 1) 1 t)))
         (projx (+ x1 (* tclamped lx))) (projy (+ y1 (* tclamped ly))))
    (sqrt (+ (* (- px projx) (- px projx)) (* (- py projy) (- py projy))))
  )
)

(defun max-inside-point (poly &optional samples)
  ; poly = list of (x y); samples = integer per axis (default 30)
  (setq samples (or samples 30))
  (setq bb (bbox-of-pts poly))
  (setq xmin (nth 0 bb) ymin (nth 1 bb) xmax (nth 2 bb) ymax (nth 3 bb))
  (setq bestpt nil bestd -1)
  (setq sx (/ (- xmax xmin) (1- samples)))
  (setq sy (/ (- ymax ymin) (1- samples)))
  (setq i 0)
  (while (<= i (1- samples))
    (setq j 0)
    (while (<= j (1- samples))
      (setq px (+ xmin (* i sx)) py (+ ymin (* j sy)))
      (if (point-in-poly (list px py) poly)
        (progn
          ; compute min distance to polygon edges
          (setq mind 1e20)
          (setq k 0)
          (while (< k (length poly))
            (setq a (nth k poly)) (setq b (nth (mod (1+ k) (length poly)) poly))
            (setq d (dist-point-seg px py (car a) (cadr a) (car b) (cadr b)))
            (if (< d mind) (setq mind d))
            (setq k (1+ k))
          )
          (if (> mind bestd) (progn (setq bestd mind) (setq bestpt (list px py))))
        )
      )
      (setq j (1+ j))
    )
    (setq i (1+ i))
  )
  (if bestpt bestpt (list (/ (+ xmin xmax) 2.0) (/ (+ ymin ymax) 2.0)))
)

;;; --- main command ---
(defun c:LABELAREAS (/ layer ss n ent entobj area label textHeight pts poly centroid inspt ms color obj)
  (setq layer (getvar "CLAYER"))
  (princ (strcat "Labeling closed polylines on layer: " layer "\n"))

  ; pick polylines on current layer (LWPOLYLINE and POLYLINE)
  (setq ss (ssget "X" (list (cons 8 layer) (cons 0 "LWPOLYLINE,POLYLINE"))))
  (if (not ss)
    (progn (princ "No polylines found on current layer.") (princ))
    (progn
      (setq ms (vla-get-ModelSpace (vla-get-ActiveDocument (vlax-get-acad-object))))
      (setq n 0)
      (repeat (sslength ss)
        (setq ent (ssname ss n) n (1+ n))
        (setq entobj (vlax-ename->vla-object ent))
        ; get area (only for closed entities; area for open will be 0)
        (setq area (vla-get-Area entobj))
        (if (> area 1e-8)
          (progn
            ; prepare label text
            (setq areaStr (rtos area 2 2))
            (setq label (strcat areaStr " m" (chr 178))) ; superscript 2

            ; get vertex list (2D)
            (setq pts (mapcar '(lambda (p) (list (car p) (cadr p))) (pts-from-lwpoly ent)))

            ; choose good insertion point
            (setq inspt (max-inside-point pts 30))

            ; choose height relative to bbox
            (setq bb (bbox-of-pts pts))
            (setq width (- (nth 2 bb) (nth 0 bb)) height (- (nth 3 bb) (nth 1 bb)))
            (setq textHeight (* (min width height) 0.12))
            (if (< textHeight 0.1) (setq textHeight 0.1))

            ; add text to ModelSpace (MTEXT) and center it
            (setq obj (vla-AddMText ms (vlax-3D-point (car inspt) (cadr inspt) 0.0) textHeight label))
            ; set attachment to middle-center (constant value 5 is often middle-center for MTEXT)
            (vl-catch-all-apply 'vla-put (list obj 'AttachmentPoint 5))
            ; set color
            (setq color (label-color))
            (vl-catch-all-apply 'vla-put (list obj 'Color color))

            (princ (strcat "Labeled area: " label " at " (rtos (car inspt) 2 2) "," (rtos (cadr inspt) 2 2) "\n"))
          ) ; progn area > 0
        ) ; if area
      ) ; repeat
    ) ; progn ss
  ) ; if
  (princ)
)

(princ "\nLoaded: LABELAREAS - run command LABELAREAS to label closed polylines on current layer.\n")
(princ)
