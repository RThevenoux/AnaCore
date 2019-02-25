#
# Copyright (C) 2014 INRA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

__author__ = 'Frederic Escudie - Plateforme bioinformatique Toulouse'
__copyright__ = 'Copyright (C) 2015 INRA'
__license__ = 'GNU General Public License'
__version__ = '2.0.0'
__email__ = 'escudie.frederic@iuct-oncopole.fr'
__status__ = 'prod'

import re
import gzip


def isGzip(filepath):
    """
    Return true if the file is gzipped.

    :param filepath: Path to the file.
    :type filepath: str.
    :return: True if the file is gziped.
    :rtype: bool
    """
    is_gzip = None
    FH_input = gzip.open(filepath)
    try:
        FH_input.readline()
        is_gzip = True
    except Exception:
        is_gzip = False
    finally:
        FH_input.close()
    return is_gzip


class Sequence:
    dna_complement = {
        'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G', 'U': 'A', 'N': 'N',
        'a': 't', 't': 'a', 'g': 'c', 'c': 'g', 'u': 'a', 'n': 'n',
        'W': 'W', 'S': 'S', 'M': 'K', 'K': 'M', 'R': 'Y', 'Y': 'R', 'B': 'V', 'V': 'B', 'D': 'H', 'H': 'D',
        'w': 'w', 's': 's', 'm': 'k', 'k': 'm', 'r': 'y', 'y': 'r', 'b': 'v', 'v': 'b', 'd': 'h', 'h': 'd'
    }

    rna_complement = {
        'A': 'U', 'T': 'A', 'G': 'C', 'C': 'G', 'U': 'A', 'N': 'N',
        'a': 'u', 't': 'a', 'g': 'c', 'c': 'g', 'u': 'a', 'n': 'n',
        'W': 'W', 'S': 'S', 'M': 'K', 'K': 'M', 'R': 'Y', 'Y': 'R', 'B': 'V', 'V': 'B', 'D': 'H', 'H': 'D',
        'w': 'w', 's': 's', 'm': 'k', 'k': 'm', 'r': 'y', 'y': 'r', 'b': 'v', 'v': 'b', 'd': 'h', 'h': 'd'
    }

    def __init__(self, id, string, description=None, quality=None):
        """
        Build and return an instance of Sequence.

        :param id: Id of the sequence.
        :type id: str
        :param string: Sequence of the sequence.
        :type string: str
        :param description: The sequence description.
        :type description: str
        :param quality: The quality of the sequence (same length as string).
        :type quality: str
        :return: The new instance.
        :rtype: Sequence
        """
        self.id = id
        self.description = description
        self.string = string
        self.quality = quality

    def dnaRevCom(self):
        """
        Return the sequence corresponding to the DNA reverse complement.

        :return: The reverse complement.
        :rtype: Sequence
        """
        return Sequence(
            self.id,
            "".join([self.dna_complement[base] for base in self.string[::-1]]),
            self.description,
            (None if self.quality is None else self.quality[::-1])
        )

    def rnaRevCom(self):
        """
        Return the sequence corresponding to the RNA reverse complement.

        :return: The reverse complement.
        :rtype: Sequence
        """
        return Sequence(
            self.id,
            "".join([self.rna_complement[base] for base in self.string[::-1]]),
            self.description,
            (None if self.quality is None else self.quality[::-1])
        )


class SequenceFileReader(object):
    @staticmethod
    def factory(filepath):
        if FastqIO.isValid(filepath):
            return FastqIO(filepath)
        elif FastaIO.isValid(filepath):
            return FastaIO(filepath)
        else:
            raise IOError("The file " + filepath + " does not have a valid format for 'SequenceFileReader'.")


class FastqIO:
    """Class to read and write in fastq file (https://en.wikipedia.org/wiki/FASTQ_format)."""

    def __init__(self, filepath, mode="r"):
        """
        Build and return an instance of FastqIO.

        :param filepath: Path to the file.
        :type filepath: str
        :param mode: Mode to open the file ('r', 'w', 'a').
        :type mode: str
        :return: The new instance.
        :rtype: FastqIO
        """
        self.filepath = filepath
        self.mode = mode
        if (mode in ["w", "a"] and filepath.endswith('.gz')) or (mode not in ["w", "a"] and isGzip(filepath)):
            self.file_handle = gzip.open(filepath, mode + "t")
        else:
            self.file_handle = open(filepath, mode)
        self.current_line_nb = 1

    def __del__(self):
        self.close()

    def close(self):
        """Close file handle it is opened."""
        if hasattr(self, 'file_handle') and self.file_handle is not None:
            self.file_handle.close()
            self.file_handle = None
            self.current_line_nb = None

    def __enter__(self):
        return(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __iter__(self):
        is_end = False
        while not is_end:
            record = self.nextSeq()
            if record is not None:
                yield(record)
            else:
                is_end = True

    def nextSeq(self):
        """
        Return the next sequence.

        :return: The next sequence or None if it is the end of file.
        :rtype: Sequence
        """
        seq_record = None
        try:
            prev_file_pos = self.file_handle.tell()
            header = self.file_handle.readline().strip()
            new_file_pos = self.file_handle.tell()
            if prev_file_pos != new_file_pos:
                # Header
                fields = header[1:].split(None, 1)
                seq_id = fields[0]
                seq_desc = fields[1] if len(fields) == 2 else None
                self.current_line_nb += 1
                # Sequence
                seq_str = self.file_handle.readline().strip()
                self.current_line_nb += 1
                # Separator
                self.file_handle.readline()
                self.current_line_nb += 1
                # Quality
                seq_qual = self.file_handle.readline().strip()
                self.current_line_nb += 1
                # Record
                seq_record = Sequence(seq_id, seq_str, seq_desc, seq_qual)
        except Exception:
            raise IOError(
                'The line {} in "{}" cannot be parsed by {}.'.format(
                    self.current_line_nb,
                    self.filepath,
                    self.__class__.__name__
                )
            )
        return seq_record

    @staticmethod
    def qualOffset(filepath):
        """
        Return the offset used to encode the quality in the file.

        :param filepath: The file path.
        :type filepath: str
        :return: The offset 33 for sanger and Illumina >=1.8, 64 for Solexa and Illumina <1.8 or None if the offset cannot be determined.
        :rtype: int
        """
        offset = None
        nb_qual = 0
        count_by_qual = {elt: 0 for elt in range(-5, 127)}
        with FastqIO(filepath) as FH_in:
            record = FH_in.nextSeq()
            while record and offset is None:
                for curr_nt, curr_ascii in zip(record.string, record.quality):
                    num_ascii = ord(curr_ascii)
                    if num_ascii < 59:
                        offset = 33
                        break
                    if curr_nt != "N":
                        nb_qual += 1
                        count_by_qual[num_ascii] += 1
                record = FH_in.nextSeq()
        if offset is None:
            checked_idx = int((nb_qual / 100) * 30)  # Index of the 30 percentile in sorted qualities
            curr_count_sum = 0
            for curr_ascii, curr_count in sorted(count_by_qual.items()):
                curr_count_sum += curr_count
                if offset is None and curr_count_sum >= checked_idx:  # 30% of qualities under this point
                    if curr_ascii > 84:  # 70% of qualities are superior than Q61 with offset 33 and Q20 with offset 64
                        offset = 64
                    else:
                        offset = 33
        return offset

    @staticmethod
    def isValid(filepath):
        """
        Return true if the file is in fastq format.

        :param filepath: The file path.
        :type filepath: str
        :return: True if the file is in fastq format.
        :rtype: bool
        """
        is_valid = False
        FH_in = FastqIO(filepath)
        try:
            seq_idx = 0
            end_of_file = False
            while seq_idx < 10 and not end_of_file:
                curr_line = FH_in.file_handle.readline()
                if not curr_line:
                    end_of_file = True
                else:
                    seq_idx += 1
                    # Record ID
                    header = curr_line
                    if not header.startswith("@"):
                        raise IOError('The record {} in "{}" has an invalid header.'.format(seq_idx, filepath))
                    # Record sequence
                    unstriped_sequence = FH_in.file_handle.readline()
                    if not unstriped_sequence:  # No line
                        raise IOError('The record {} in "{}" is truncated.'.format(seq_idx, filepath))
                    if not re.search("^[A-Za-z]*$", unstriped_sequence.strip()):
                        raise IOError('The sequence {} in "{}" contains invalid characters.'.format(seq_idx, filepath))
                    # Record separator
                    unstriped_separator = FH_in.file_handle.readline()
                    if not unstriped_separator:  # No line
                        raise IOError('The record {} in "{}" is truncated.'.format(seq_idx, filepath))
                    # Record quality
                    unstriped_quality = FH_in.file_handle.readline()
                    # Sequence and quality length
                    if len(unstriped_sequence.strip()) != len(unstriped_quality.strip()):
                        raise IOError('The record {} in "{}" contains a sequence and a quality with different length.'.format(seq_idx, filepath))
            is_valid = True
        except Exception:
            pass
        finally:
            FH_in.close()
        return is_valid

    @staticmethod
    def nbSeq(filepath):
        """
        Return the number of sequences in file.

        :param filepath: Path to the file.
        :type filepath: str
        :return: The number of sequences.
        :rtype: int
        """
        nb_line = 0
        if isGzip(filepath):
            with gzip.open(filepath, "rt") as FH_in:
                for line in FH_in:
                    nb_line += 1
        else:
            with open(filepath, "r") as FH_in:
                for line in FH_in:
                    nb_line += 1
        return int(nb_line / 4)

    def write(self, sequence_record):
        """
        Write record lines in file.

        :param sequence_record: The record to write.
        :type sequence_record: Sequence
        """
        self.file_handle.write(self.seqToFastqLine(sequence_record) + "\n")
        self.current_line_nb += 1

    def seqToFastqLine(self, sequence):
        """
        Return the sequence in fastq format.

        :param sequence: The sequence to process.
        :type sequence: Sequence
        :return: The sequence.
        :rtype: str
        """
        seq = "@" + sequence.id + (" " + sequence.description if sequence.description is not None else "")
        seq += "\n" + sequence.string
        seq += "\n+"
        seq += "\n" + sequence.quality
        return seq


class FastaIO:
    """Class to read and write in fasta file (https://en.wikipedia.org/wiki/FASTA_format)."""

    def __init__(self, filepath, mode="r"):
        """
        Build and return an instance of FastaIO.

        :param filepath: Path to the file.
        :type filepath: str
        :param mode: Mode to open the file ('r', 'w', 'a').
        :type mode: str
        :return: The new instance.
        :rtype: FastaIO
        """
        self.filepath = filepath
        self.mode = mode
        if (mode in ["w", "a"] and filepath.endswith('.gz')) or (mode not in ["w", "a"] and isGzip(filepath)):
            self.file_handle = gzip.open(filepath, mode + "t")
        else:
            self.file_handle = open(filepath, mode)
        self.current_line_nb = 1
        self._next_id = None
        self._end_of_file = False

    def __del__(self):
        self.close()

    def close(self):
        """Close file handle it is opened."""
        if hasattr(self, 'file_handle') and self.file_handle is not None:
            self.file_handle.close()
            self.file_handle = None
            self.current_line_nb = None

    def __enter__(self):
        return(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __iter__(self):
        is_end = False
        while not is_end:
            record = self.nextSeq()
            if record is not None:
                yield(record)
            else:
                is_end = True

    def nextSeq(self):
        """
        Return the next sequence.

        :return: The next sequence.
        :rtype: Sequence
        """
        seq_record = None
        if not self._end_of_file:
            line = ""
            try:
                # First line in file
                if self.current_line_nb == 1:
                    self._next_id = self.file_handle.readline().strip()
                    self.current_line_nb += 1
                # Sequence
                seq_str = ""
                while not line.startswith('>'):
                    seq_str += line.strip()
                    line = self.file_handle.readline()
                    if not line:
                        line = None
                        self._end_of_file = True
                        break
                    self.current_line_nb += 1
                fields = self._next_id[1:].split(None, 1)
                seq_id = fields[0]
                seq_desc = fields[1].strip() if len(fields) == 2 else None
                seq_record = Sequence(seq_id, seq_str, seq_desc)
                self._next_id = line  # next seq_id
            except Exception:
                raise IOError(
                    'The line {} in "{}" cannot be parsed by {}.\ncontent: {}'.format(
                        self.current_line_nb,
                        self.filepath,
                        self.__class__.__name__,
                        line
                    )
                )
        return seq_record

    @staticmethod
    def isValid(filepath):
        """
        Return true if the file is in fasta format.

        :param filepath: The file path.
        :type filepath: str
        :return: True if the file is in fasta format.
        :rtype: bool
        """
        is_valid = False
        FH_in = FastaIO(filepath)
        try:
            seq_idx = 0
            prev_is_header = None
            end_of_file = False
            while seq_idx < 10 and not end_of_file:
                curr_line = FH_in.file_handle.readline()
                if not curr_line:
                    end_of_file = True
                else:
                    if curr_line.startswith(">"):
                        if prev_is_header:
                            raise IOError('The fasta file "{}" cotains an header without sequence.'.format(filepath))
                        prev_is_header = True
                        seq_idx += 1
                    else:
                        if seq_idx == 0:  # The fasta file do not starts with ">"
                            raise IOError('The fasta file "{}" does not start with ">".'.format(filepath))
                        prev_is_header = False
            is_valid = True
        except Exception:
            pass
        finally:
            FH_in.close()
        return is_valid

    @staticmethod
    def nbSeq(filepath):
        """
        Return the number of sequences in file.

        :param filepath: Path to the file.
        :type filepath: str
        :return: The number of sequences.
        :rtype: int
        """
        nb_seq = 0
        if isGzip(filepath):
            with gzip.open(filepath, "rt") as FH_in:
                for line in FH_in:
                    if line.startswith(">"):
                        nb_seq += 1
        else:
            with open(filepath, "r") as FH_in:
                for line in FH_in:
                    if line.startswith(">"):
                        nb_seq += 1
        return nb_seq

    def write(self, sequence_record):
        """
        Write record lines in file.

        :param sequence_record: The record to write.
        :type sequence_record: Sequence
        """
        self.file_handle.write(self.seqToFastaLine(sequence_record) + "\n")
        self.current_line_nb += 1

    def seqToFastaLine(self, sequence):
        """
        Return the sequence in fasta format.

        :param sequence: The sequence to process.
        :type sequence: Sequence
        :return: The sequence.
        :rtype: str
        """
        header = ">" + sequence.id + (" " + sequence.description if sequence.description is not None else "")
        return header + "\n" + sequence.string
