(define (manual-levels filename
                       red_low_in   red_high_in  
                       green_low_in green_high_in
                       blue_low_in  blue_high_in)
  (let* ( (image    (car (gimp-file-load RUN-NONINTERACTIVE filename filename)))
          (drawable (car (gimp-image-get-active-layer image))) )
    (gimp-drawable-levels drawable HISTOGRAM-RED red_low_in red_high_in
                          FALSE 1.0 0 1.0 FALSE)
    (gimp-drawable-levels drawable HISTOGRAM-GREEN green_low_in green_high_in
                          FALSE 1.0 0 1.0 FALSE)
    (gimp-drawable-levels drawable HISTOGRAM-BLUE blue_low_in blue_high_in
                          FALSE 1.0 0 1.0 FALSE)
    (gimp-file-save RUN-NONINTERACTIVE image drawable filename filename)
    (gimp-image-delete image)))
