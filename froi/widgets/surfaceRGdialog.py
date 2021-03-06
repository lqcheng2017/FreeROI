import numpy as np
from PyQt4 import QtGui, QtCore
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, MultiCursor

from ..io.surf_io import read_scalar_data
from ..algorithm.regiongrow import RegionGrow
from ..algorithm.tools import get_curr_hemi, get_curr_overlay, slide_win_smooth, VlineMover
from ..algorithm.meshtool import get_n_ring_neighbor


class SurfaceRGDialog(QtGui.QDialog):

    rg_types = ['srg', 'arg', 'crg']

    def __init__(self, model, tree_view_control, surf_view, parent=None):
        super(SurfaceRGDialog, self).__init__(parent)
        self.setWindowTitle("surfRG")
        self._surf_view = surf_view
        self.tree_view_control = tree_view_control
        self.model = model

        self.hemi = self._get_curr_hemi()
        # FIXME 'inflated' should be replaced with surf_type in the future
        self.surf = self.hemi.surfaces['inflated']
        self.hemi_vtx_number = self.surf.get_vertices_num()
        # NxM array, N is the number of vertices,
        # M is the number of measurements or time points.
        self.X = None

        self.rg_type = 'arg'
        self.mask = None
        self.seeds_id = []
        self.stop_criteria = [500]
        self.n_ring = 1
        self.group_idx = 'new'  # specify current seed group's index
        self.cut_line = []  # a list of vertices' id which plot a line
        self.r_idx_sm = None
        self.smoothness = None

        self._init_gui()
        self._create_actions()

        self._surf_view.seed_flag = True

    def _init_gui(self):
        # Initialize widgets
        group_idx_label = QtGui.QLabel('seed group:')
        self._group_idx_combo = QtGui.QComboBox()
        self._group_idx_combo.addItem(self.group_idx)

        seeds_label = QtGui.QLabel("seeds:")
        self._seeds_edit = QtGui.QLineEdit()
        self._seeds_edit.setText('peak value vertex')

        self._stop_label = QtGui.QLabel("stop_criteria:")
        self._stop_edit = QtGui.QLineEdit()
        self._stop_edit.setText(str(self.stop_criteria[0]))

        ring_label = QtGui.QLabel("n_ring:")
        self._ring_spin = QtGui.QSpinBox()
        self._ring_spin.setMinimum(1)
        self._ring_spin.setValue(self.n_ring)

        rg_type_label = QtGui.QLabel('RG-type')
        self._rg_type_combo = QtGui.QComboBox()
        self._rg_type_combo.addItems(self.rg_types)
        self._rg_type_combo.setCurrentIndex(self.rg_types.index(self.rg_type))

        self._scalar_button = QtGui.QPushButton("add scalar")
        self._mask_button = QtGui.QPushButton('add mask')

        self._cutoff_button1 = QtGui.QPushButton('start cutoff')
        self._cutoff_button2 = QtGui.QPushButton('stop cutoff')
        self._cutoff_button1.setVisible(False)
        self._cutoff_button2.setVisible(False)
        self._cutoff_button2.setEnabled(False)

        self._ok_button = QtGui.QPushButton("OK")
        self._cancel_button = QtGui.QPushButton("Cancel")

        # layout
        grid_layout = QtGui.QGridLayout()
        grid_layout.addWidget(rg_type_label, 0, 0)
        grid_layout.addWidget(self._rg_type_combo, 0, 1)
        grid_layout.addWidget(group_idx_label, 1, 0)
        grid_layout.addWidget(self._group_idx_combo, 1, 1)
        grid_layout.addWidget(seeds_label, 2, 0)
        grid_layout.addWidget(self._seeds_edit, 2, 1)
        grid_layout.addWidget(self._stop_label, 3, 0)
        grid_layout.addWidget(self._stop_edit, 3, 1)
        grid_layout.addWidget(ring_label, 4, 0)
        grid_layout.addWidget(self._ring_spin, 4, 1)
        grid_layout.addWidget(self._scalar_button, 5, 0)
        grid_layout.addWidget(self._mask_button, 5, 1)
        grid_layout.addWidget(self._cutoff_button1, 6, 0)
        grid_layout.addWidget(self._cutoff_button2, 6, 1)
        grid_layout.addWidget(self._ok_button, 7, 0)
        grid_layout.addWidget(self._cancel_button, 7, 1)
        self.setLayout(grid_layout)

    def _create_actions(self):
        # connect
        self.connect(self._ok_button, QtCore.SIGNAL("clicked()"), self._start_surfRG)
        self.connect(self._cancel_button, QtCore.SIGNAL("clicked()"), self.close)
        self.connect(self._seeds_edit, QtCore.SIGNAL("textEdited(QString)"), self._set_seeds_id)
        self.connect(self._stop_edit, QtCore.SIGNAL("textEdited(QString)"), self._set_stop_criteria)
        self._ring_spin.valueChanged.connect(self._set_n_ring)
        self._rg_type_combo.currentIndexChanged.connect(self._set_rg_type)
        self._group_idx_combo.currentIndexChanged.connect(self._set_group_idx)
        self.connect(self._scalar_button, QtCore.SIGNAL("clicked()"), self._scalar_dialog)
        self.connect(self._mask_button, QtCore.SIGNAL("clicked()"), self._mask_dialog)
        self.connect(self._cutoff_button1, QtCore.SIGNAL("clicked()"), self._start_cutoff)
        self.connect(self._cutoff_button2, QtCore.SIGNAL("clicked()"), self._stop_cutoff)
        self._surf_view.seed_picked.connect(self._set_seeds_edit_text)

    def _mask_dialog(self):

        fpath = QtGui.QFileDialog().getOpenFileName(self, 'Open mask file', './',
                                                    'mask files(*.nii *.nii.gz *.mgz *.mgh *.label)')
        if not fpath:
            return
        self.mask, _ = read_scalar_data(fpath, self.hemi_vtx_number)

    def _scalar_dialog(self):

        fpaths = QtGui.QFileDialog().getOpenFileNames(self, "Open scalar file", "./")

        if not fpaths:
            return
        self.X = np.zeros((self.hemi_vtx_number,))
        for fpath in fpaths:
            data, _ = read_scalar_data(fpath, self.hemi_vtx_number)
            self.X = np.c_[self.X, data]
        self.X = np.delete(self.X, 0, 1)

    def _start_cutoff(self):
        self._cutoff_button1.setEnabled(False)
        self._cutoff_button2.setEnabled(True)
        self._surf_view.seed_flag = False
        self._surf_view.scribing_flag = True
        self.cut_line = []

    def _stop_cutoff(self):
        self._surf_view.seed_flag = True
        self._surf_view.scribing_flag = False
        self._cutoff_button1.setEnabled(True)
        self._cutoff_button2.setEnabled(False)
        self.cut_line = list(self._surf_view.path)
        self._surf_view.plot_start = None
        self._surf_view.path = []

    def _set_group_idx(self):

        self.group_idx = str(self._group_idx_combo.currentText())
        if self.group_idx == 'new':
            self._seeds_edit.setText('')
        else:
            idx = int(self.group_idx)
            text = ','.join(map(str, self.seeds_id[idx]))
            self._seeds_edit.setText(text)

    def _set_rg_type(self):
        self.rg_type = str(self._rg_type_combo.currentText())
        if self.rg_type == 'crg':
            self._stop_edit.setVisible(False)
            self._stop_label.setVisible(False)
            self._scalar_button.setVisible(False)
            self._mask_button.setVisible(False)
            self._cutoff_button1.setVisible(True)
            self._cutoff_button2.setVisible(True)
        else:
            self._stop_edit.setVisible(True)
            self._stop_label.setVisible(True)
            self._scalar_button.setVisible(True)
            self._mask_button.setVisible(True)
            self._cutoff_button1.setVisible(False)
            self._cutoff_button2.setVisible(False)
            self._stop_cutoff()
            self.cut_line = []

    def _set_seeds_edit_text(self):

        if self.group_idx == 'new':
            idx = len(self.seeds_id)
            self.seeds_id.append([self._surf_view.point_id])
            self.group_idx = str(idx)
            self._group_idx_combo.addItem(self.group_idx)
            self._group_idx_combo.setCurrentIndex(idx+1)
        else:
            idx = int(self.group_idx)
            self.seeds_id[idx].append(self._surf_view.point_id)
        text = ','.join(map(str, self.seeds_id[idx]))
        self._seeds_edit.setText(text)

    def _set_stop_criteria(self):

        text_list = self._stop_edit.text().split(',')
        while '' in text_list:
            text_list.remove('')
        if len(text_list) == len(self.seeds_id):
            self.stop_criteria = np.array(text_list, dtype="int")
        elif len(text_list) == 0:
            pass
        else:
            # If the number of stop_criteria is not equal to seeds,
            # then we use its first stop criteria for all seeds.
            self.stop_criteria = np.array(text_list[0], dtype="int")

    def _set_seeds_id(self):

        text_list = self._seeds_edit.text().split(',')
        while '' in text_list:
            text_list.remove('')
        if self.group_idx == 'new':
            if text_list:
                idx = len(self.seeds_id)
                self.seeds_id.append(map(int, text_list))
                self.group_idx = str(idx)
                self._group_idx_combo.addItem(self.group_idx)
                self._group_idx_combo.setCurrentIndex(idx+1)
        else:
            idx = int(self.group_idx)
            if text_list:
                self.seeds_id[idx] = map(int, text_list)
            else:
                end_item_idx = len(self.seeds_id)
                self.seeds_id.pop(idx)
                self._group_idx_combo.removeItem(end_item_idx)
                self.group_idx = 'new'
                self._group_idx_combo.setCurrentIndex(0)
        self._set_stop_criteria()

    def _set_n_ring(self):
        self.n_ring = int(self._ring_spin.value())

    def _start_surfRG(self):

        rg = RegionGrow()
        if self.rg_type == 'arg':
            if self.X is None:
                ol = self._get_curr_overlay()
                if not ol:
                    return None
                self.X = ol.get_data()

            # ------------------select a assessment function-----------------
            assess_type, ok = QtGui.QInputDialog.getItem(
                    self,
                    'select a assessment function',
                    'assessments:',
                    rg.get_assess_types()
            )

            # ------------------If ok, start arg!-----------------
            if ok and assess_type != '':
                rg.set_assessment(assess_type)
                rg.surf2regions(self.surf, self.X, self.mask, self.n_ring)
                rg_result, self.evolved_regions, self.region_assessments, self.assess_step, r_outer_value =\
                    rg.arg_parcel(self.seeds_id, self.stop_criteria, whole_results=True)

                # -----------------plot diagrams------------------
                num_axes = len(self.evolved_regions)
                fig, self.axes = plt.subplots(num_axes, 2)
                if num_axes == 1:
                    self.axes = np.array([self.axes])
                self.vline_movers = np.zeros_like(self.axes[:, 0])  # store vline movers
                self.cursors = np.zeros_like(self.axes)  # store cursors, hold references
                self.slider_axes = np.zeros_like(self.axes[:, 0])
                self.sm_sliders = []  # store smooth sliders, hold references
                for r_idx, r in enumerate(self.evolved_regions):
                    # plot region outer boundary assessment curve
                    self.axes[r_idx][1].plot(r_outer_value[r_idx], 'b.-')
                    self.axes[r_idx][1].set_ylabel('amplitude')
                    self.axes[r_idx][1].set_title('outer boundary value for seed {}'.format(r_idx))

                    # plot assessment curve
                    self.r_idx_sm = r_idx
                    self.smoothness = 0
                    self._sm_update_axes()

                    # add slider
                    ax_pos = self.axes[r_idx][0].get_position()
                    slider_ax = fig.add_axes([ax_pos.x1-0.15, ax_pos.y0+0.005, 0.15, 0.015])
                    sm_slider = Slider(slider_ax, 'smoothness', 0, 10, 0, '%d', dragging=False)
                    sm_slider.on_changed(self._on_smooth_changed)
                    self.slider_axes[r_idx] = slider_ax
                    self.sm_sliders.append(sm_slider)

                    # axes hold off
                    self.axes[r_idx][0].hold(False)
                self.axes[-1][1].set_xlabel('contrast step/component')
                self.cursor = MultiCursor(fig.canvas, self.axes.ravel(),
                                          ls='dashed', lw=0.5, c='g', horizOn=True)
                fig.canvas.set_window_title('assessment curves')
                fig.canvas.mpl_connect('button_press_event', self._on_clicked)
                plt.show()
            else:
                QtGui.QMessageBox.warning(
                    self,
                    'Warning',
                    'You have to specify a assessment function for arg!',
                    QtGui.QMessageBox.Yes
                )
                return None

        elif self.rg_type == 'srg':
            if self.X is None:
                ol = self._get_curr_overlay()
                if not ol:
                    return None
                self.X = ol.get_data()

            rg.surf2regions(self.surf, self.X, self.mask, self.n_ring)
            rg_result = rg.srg_parcel(self.seeds_id, self.stop_criteria)

        elif self.rg_type == 'crg':
            ol = get_curr_overlay(self.tree_view_control.currentIndex())
            if ol:
                data = ol.get_data()
                data = np.mean(data, 1)
                mask = data.reshape((data.shape[0],))
                idx = np.where(mask < ol.get_min())
                mask[idx] = 0
                edge_list = get_n_ring_neighbor(self.surf.get_faces(), n=self.n_ring, mask=mask)
            else:
                edge_list = get_n_ring_neighbor(self.surf.get_faces(), n=self.n_ring)

            for cut_vtx in self.cut_line:
                edge_list[cut_vtx] = set()
            rg_result = rg.connectivity_grow(self.seeds_id, edge_list)

        else:
            raise RuntimeError("The region growing type must be arg, srg and crg at present!")

        self._show_result(rg_result)
        self.close()

    def _get_curr_hemi(self):

        hemi = get_curr_hemi(self.tree_view_control.currentIndex())
        if not hemi:
            QtGui.QMessageBox.warning(
                    self, 'Error',
                    'Get hemisphere failed!\nYou may have not selected any hemisphere!',
                    QtGui.QMessageBox.Yes
            )
            self.close()  # FIXME may be a bug
        return hemi

    def _get_curr_overlay(self):
        """
        If no scalar data is selected, the program will
        get current overlay's data as region growing's data.
        """

        ol = get_curr_overlay(self.tree_view_control.currentIndex())
        if not ol:
            QtGui.QMessageBox.warning(
                    self,
                    'Warning',
                    'Get overlay failed!\nYou may have not selected any overlay!',
                    QtGui.QMessageBox.Yes
            )
        return ol

    def _show_result(self, rg_result):
        """
        Add RG's result as tree items
        """
        for r in rg_result:
            if self.rg_type == 'srg' or self.rg_type == 'arg':
                labeled_vertices = r.get_vertices()
            elif self.rg_type == 'crg':
                labeled_vertices = list(r)
            else:
                raise RuntimeError("The region growing type must be arg, srg and crg at present!")
            data = np.zeros((self.hemi_vtx_number,), np.int)
            data[labeled_vertices] = 1
            self.model.add_item(self.tree_view_control.currentIndex(), data,
                                islabel=True, colormap='blue')

    def _on_clicked(self, event):
        if event.button == 3 and event.inaxes in self.axes[:, 0]:
            # do something on right click
            # find current evolved region
            r_idx = np.where(self.axes[:, 0] == event.inaxes)[0][0]
            r = self.evolved_regions[r_idx]

            # get vertices included in the evolved region
            index = self.vline_movers[r_idx].x[0]
            end_index = int((index+1) * self.assess_step)
            labeled_vertices = set()
            for region in r.get_component()[:end_index]:
                labeled_vertices.update(region.get_vertices())
            labeled_vertices = list(labeled_vertices)

            # visualize these labeled vertices
            data = np.zeros((self.hemi_vtx_number,), np.int)
            data[labeled_vertices] = 1
            self.model.add_item(self.tree_view_control.currentIndex(), data,
                                islabel=True, colormap='blue')
        elif event.button == 1 and event.inaxes in self.slider_axes:
            # do something on left click
            # find current evolved region
            self.r_idx_sm = np.where(self.slider_axes == event.inaxes)[0][0]
            if self.smoothness is not None:
                # indicate that self._on_click is performed later than self._on_smooth_changed
                # to ensure that self.r_idx_sm is got before smoothing
                self._sm_update_axes()

    def _on_smooth_changed(self, val):
        self.smoothness = int(val)
        if self.r_idx_sm is not None:
            # indicate that self._on_click is performed earlier than self._on_smooth_changed
            # to ensure that self.r_idx_sm is got before smoothing
            self._sm_update_axes()

    def _sm_update_axes(self):
        smoothed_curve = slide_win_smooth(self.region_assessments[self.r_idx_sm], self.smoothness)
        self.axes[self.r_idx_sm][0].plot(smoothed_curve, 'b.-')
        self.axes[self.r_idx_sm][0].set_title('curve for seed {}'.format(self.r_idx_sm))
        if self.r_idx_sm == len(self.axes)-1:
            self.axes[self.r_idx_sm][0].set_xlabel('contrast step/component')
        self.axes[self.r_idx_sm][0].set_ylabel('assessed value')

        # initialize vline
        max_index = np.argmax(smoothed_curve)
        vline = self.axes[self.r_idx_sm][0].axvline(max_index)
        # instance VlineMover
        self.vline_movers[self.r_idx_sm] = VlineMover(vline, True)

        # reset
        self.r_idx_sm = None
        self.smoothness = None

    def close(self):

        self._surf_view.seed_flag = False
        QtGui.QDialog.close(self)
